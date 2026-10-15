// WebGL2 plumbing: background + set composite, instanced particles, post/accumulate, output.

const VS_FULL = `#version 300 es
const vec2 P[3] = vec2[3](vec2(-1.,-1.), vec2(3.,-1.), vec2(-1.,3.));
out vec2 vUv;
void main(){ vec2 p = P[gl_VertexID]; vUv = p*.5+.5; gl_Position = vec4(p,0.,1.); }`;

// Background light (room tone, phone glow, volumetric beam) with the 2D set layer graded on top.
const FS_BG = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform vec2 uRes;
uniform sampler2D uSet;
uniform vec3 uBase, uBase2;
uniform vec4 uGlow;      // xy px, radius px, intensity
uniform vec3 uGlowCol;
uniform vec4 uGlow2;     // secondary soft glow
uniform vec3 uGlow2Col;
uniform vec4 uBeam;      // A.xy, B.xy (px)
uniform vec4 uBeamP;     // width at A, width at B, intensity, shimmer time
uniform vec3 uBeamCol;
uniform float uVig, uFreeze, uSetAlpha, uLift;
float h(vec2 p){ return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
float vn(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
  return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
void main(){
  vec2 px = vec2(vUv.x, 1.-vUv.y) * uRes;
  vec2 q = px / uRes.y;
  vec3 c = mix(uBase2, uBase, smoothstep(0., 1., vUv.y));
  float d = length(px - uGlow.xy) / max(uGlow.z, 1.);
  c += uGlowCol * uGlow.w * (exp(-d*d*2.2) * .75 + .25 / (1. + d*d*6.));
  float d2 = length(px - uGlow2.xy) / max(uGlow2.z, 1.);
  c += uGlow2Col * uGlow2.w * exp(-d2*d2*2.);
  // beam: soft wedge from A to B
  vec2 A = uBeam.xy, B = uBeam.zw, ab = B - A;
  float L = length(ab);
  if (uBeamP.z > 0. && L > 1.) {
    vec2 dir = ab / L, nrm = vec2(-dir.y, dir.x);
    float along = dot(px - A, dir) / L, across = dot(px - A, nrm);
    float w = mix(uBeamP.x, uBeamP.y, clamp(along, 0., 1.));
    float m = smoothstep(1., .35, abs(across) / w) * smoothstep(0., .12, along) * smoothstep(1.15, .7, along);
    float sh = .78 + .22 * vn(vec2(across / 90. + uBeamP.w * .05, along * 3. - uBeamP.w * .11));
    c += uBeamCol * uBeamP.z * m * sh;
  }
  vec4 s = texture(uSet, vec2(vUv.x, 1. - vUv.y)) * uSetAlpha;   // premultiplied
  c = c * (1. - s.a) + s.rgb;
  // freeze grade: the world goes colder and flatter
  float lum = dot(c, vec3(.299,.587,.114));
  c = mix(c, vec3(lum) * vec3(.86, .95, 1.12), uFreeze * .55);
  c += uLift;
  // vignette
  vec2 v = vUv - .5; v.x *= uRes.x / uRes.y;
  c *= mix(1., smoothstep(1.25, .25, length(v)), uVig);
  o = vec4(c, 1.);
}`;

const VS_PART = `#version 300 es
layout(location=0) in vec4 iPos;   // x, y (px), size (px half-extent), type
layout(location=1) in vec4 iCol;   // rgb intensity (premult), alpha
layout(location=2) in vec4 iPar;
uniform vec2 uRes;
out vec2 vL; out vec4 vCol; out vec4 vPar; flat out float vType; out vec2 vPx;
const vec2 C[6] = vec2[6](vec2(-1.,-1.), vec2(1.,-1.), vec2(1.,1.), vec2(-1.,-1.), vec2(1.,1.), vec2(-1.,1.));
void main(){
  vec2 c = C[gl_VertexID];
  vec2 p = iPos.xy + c * iPos.z;
  vL = c; vCol = iCol; vPar = iPar; vType = iPos.w; vPx = p;
  gl_Position = vec4(p / uRes * 2. - 1., 0., 1.) * vec4(1., -1., 1., 1.);
}`;

const FS_PART = `#version 300 es
precision highp float;
in vec2 vL; in vec4 vCol; in vec4 vPar; flat in float vType; in vec2 vPx;
uniform vec4 uClip;      // birds are clipped to the window glass (x0,y0,x1,y1 px)
out vec4 o;
float seg(vec2 p, vec2 a, vec2 b){ vec2 pa=p-a, ba=b-a; float h=clamp(dot(pa,ba)/dot(ba,ba),0.,1.); return length(pa-ba*h); }
mat2 rot(float a){ float c=cos(a), s=sin(a); return mat2(c,-s,s,c); }
void main(){
  float r = length(vL);
  float a = 0.;
  float glow = 0.;
  int t = int(vType + .5);
  if (t == 0) {                 // soft mote: core + halo. par.x = core radius (0..1)
    float core = vPar.x;
    a = smoothstep(core, core * .55, r);
    glow = exp(-r * r * 9.) * vPar.y;
  } else if (t == 1) {          // droplet: ellipse along angle par.x, aspect par.y
    vec2 p = rot(vPar.x) * vL; p.y *= vPar.y;
    float d = length(p);
    a = smoothstep(.62, .46, d);
    glow = exp(-d * d * 6.) * .25;
  } else if (t == 2) {          // bird: two wings, angle par.x, flap par.y (-1..1)
    vec2 p = rot(vPar.x) * vL;
    float f = vPar.y;
    vec2 lw = vec2(-.85, -.18 - .55 * f), rw = vec2(.85, -.18 - .55 * f);
    vec2 lm = vec2(-.42, .02 + .1 * f), rm = vec2(.42, .02 + .1 * f);
    float d = min(min(seg(p, vec2(0.,.08), lm), seg(p, lm, lw)), min(seg(p, vec2(0.,.08), rm), seg(p, rm, rw)));
    d = min(d, length(p - vec2(0., .1)) - .05);
    a = smoothstep(.085, .045, d);
    if (vPx.x < uClip.x || vPx.y < uClip.y || vPx.x > uClip.z || vPx.y > uClip.w) a = 0.;
  } else if (t == 3) {          // grid dot: par.x fill (0..1), par.y glow, par.z ring radius, par.w ring width
    float R = vPar.z;
    float ring = smoothstep(vPar.w, vPar.w * .4, abs(r - R));
    float fill = smoothstep(R + .02, R - .06, r);
    a = max(ring * (1. - vPar.x) * .7, fill * vPar.x);
    glow = exp(-r * r / (R * R) * .9) * vPar.y;
  } else if (t == 4) {          // ring / shock: par.x radius, par.y width
    a = smoothstep(vPar.y, 0., abs(r - vPar.x));
  } else if (t == 5) {          // amber "you": hot core, warm halo, wide breath
    float core = vPar.x;
    a = smoothstep(core, core * .7, r);
    glow = exp(-r * r / (core * core) * .45) * .55 + exp(-r * r * 5.) * vPar.y;
  }
  float k = clamp(a + glow, 0., 4.) * vCol.a;
  o = vec4(vCol.rgb * k, a * vCol.a);
}`;

// Post: freeze ripple, overlay type, write weighted into the accumulator.
const FS_POST = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform sampler2D uScene, uOv;
uniform vec2 uRes;
uniform vec4 uRipple;    // center px, radius px, strength
uniform float uWeight, uOvAlpha, uShake;
uniform vec2 uShakeOff;
uniform vec4 uLens;      // peephole: center px (top-left origin), radius px, field scale; z = 0 -> off
void main(){
  vec2 px = vUv * uRes;
  vec2 c = vec2(uRipple.x, uRes.y - uRipple.y);
  vec2 dv = px - c; float d = length(dv);
  float w = exp(-pow((d - uRipple.z) / 46., 2.)) * uRipple.w;
  vec2 off = (d > 0. ? dv / d : vec2(0.)) * w * 14.;
  vec2 uv = (px - off + uShakeOff) / uRes;
  vec3 col = texture(uScene, uv).rgb;
  if (uLens.z > 0.) {
    // fisheye: the middle swells, the rim crushes, colour fringes at the edge
    vec2 lc = vec2(uLens.x, uRes.y - uLens.y);
    vec2 q = (px + uShakeOff - lc) / uLens.z;
    float r = length(q);
    vec2 dir = r > 0. ? q / r : vec2(0.);
    float k = r * (0.42 + 0.58 * r * r);
    vec2 base = lc + dir * uLens.z * uLens.w;
    col.r = texture(uScene, (lc + dir * k * 1.012 * uLens.z * uLens.w) / uRes).r;
    col.g = texture(uScene, (lc + dir * k * uLens.z * uLens.w) / uRes).g;
    col.b = texture(uScene, (lc + dir * k * 0.988 * uLens.z * uLens.w) / uRes).b;
    col *= smoothstep(1.0, 0.965, r) * (1. - 0.6 * r * r);
    col += vec3(.5, .6, .55) * .05 * smoothstep(.93, 1., r) * smoothstep(1.02, 1., r);   // glass rim
  }
  // a faint cold seam along the ripple front
  col += vec3(.55, .75, 1.) * w * .05;
  vec4 ov = texture(uOv, vec2(vUv.x, 1. - vUv.y) + uShakeOff * vec2(1.,-1.) / uRes) * uOvAlpha;
  col = col * (1. - ov.a) + ov.rgb;
  o = vec4(col * uWeight, uWeight);
}`;

// Output: soft shoulder, grain seeded by the (world) clock, dither, flip for readback.
const FS_OUT = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform sampler2D uAcc;
uniform float uSeed, uGrain;
float h(vec3 p){ p = fract(p * vec3(.1031, .1030, .0973)); p += dot(p, p.yxz + 33.33); return fract((p.x + p.y) * p.z); }
vec3 shoulder(vec3 c){ return mix(c, .8 + .2 * (1. - exp(-(c - .8) / .2)), step(.8, c)); }
void main(){
  vec2 uv = vec2(vUv.x, 1. - vUv.y);
  vec3 c = max(texture(uAcc, uv).rgb, 0.);
  c = shoulder(c);
  vec2 p = gl_FragCoord.xy;
  float g = (h(vec3(p, uSeed)) + h(vec3(p + 17.1, uSeed + 3.7)) - 1.);
  float l = dot(c, vec3(.299, .587, .114));
  c += g * uGrain * (.35 + .65 * smoothstep(.0, .25, l)) ;
  c = pow(max(c, 0.), vec3(1. / 1.0));
  c += (h(vec3(p, uSeed * 1.37 + 9.)) - .5) / 255.;
  o = vec4(clamp(c, 0., 1.), 1.);
}`;

function compile(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) + '\n' + src);
  return s;
}
function program(gl, vs, fs) {
  const p = gl.createProgram();
  gl.attachShader(p, compile(gl, gl.VERTEX_SHADER, vs));
  gl.attachShader(p, compile(gl, gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  const u = {};
  const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) { const info = gl.getActiveUniform(p, i); u[info.name] = gl.getUniformLocation(p, info.name); }
  return { p, u };
}

function target(gl, W, H, internal, format, type, filter = gl.LINEAR) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texImage2D(gl.TEXTURE_2D, 0, internal, W, H, 0, format, type, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const fb = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) throw new Error('fbo incomplete');
  return { tex, fb };
}

function srcTexture(gl) {
  const t = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, t);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  return t;
}

export function createGL(canvas, W, H) {
  const gl = canvas.getContext('webgl2', { antialias: false, premultipliedAlpha: false, preserveDrawingBuffer: true });
  if (!gl) throw new Error('no webgl2');
  if (!gl.getExtension('EXT_color_buffer_float')) throw new Error('no float render targets');
  gl.getExtension('EXT_float_blend');
  const bg = program(gl, VS_FULL, FS_BG);
  const part = program(gl, VS_PART, FS_PART);
  const post = program(gl, VS_FULL, FS_POST);
  const out = program(gl, VS_FULL, FS_OUT);
  const scene = target(gl, W, H, gl.RGBA16F, gl.RGBA, gl.HALF_FLOAT);
  // RGBA32F is not filterable without OES_texture_float_linear: sample it NEAREST
  const acc = target(gl, W, H, gl.RGBA32F, gl.RGBA, gl.FLOAT, gl.NEAREST);
  const fin = target(gl, W, H, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE);
  const setTex = srcTexture(gl), ovTex = srcTexture(gl);
  const vao = gl.createVertexArray();
  const pvao = gl.createVertexArray();
  const pbuf = gl.createBuffer();
  gl.bindVertexArray(pvao);
  gl.bindBuffer(gl.ARRAY_BUFFER, pbuf);
  for (let i = 0; i < 3; i++) {
    gl.enableVertexAttribArray(i);
    gl.vertexAttribPointer(i, 4, gl.FLOAT, false, 48, i * 16);
    gl.vertexAttribDivisor(i, 1);
  }
  gl.bindVertexArray(null);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);

  const upload = (tex, cv) => {
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, cv);
  };

  return {
    gl, scene, acc, fin,
    beginFrame() {
      gl.bindFramebuffer(gl.FRAMEBUFFER, acc.fb);
      gl.viewport(0, 0, W, H);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
    },
    // One sub-frame: S = scene state from the timeline, setCv/ovCv = 2D layers, parts = Float32Array.
    subFrame(S, setCv, ovCv, parts, nParts, weight) {
      upload(setTex, setCv);
      upload(ovTex, ovCv);
      // 1. background + set
      gl.bindFramebuffer(gl.FRAMEBUFFER, scene.fb);
      gl.viewport(0, 0, W, H);
      gl.disable(gl.BLEND);
      gl.useProgram(bg.p);
      gl.bindVertexArray(vao);
      const u = bg.u, b = S.bg;
      gl.uniform2f(u.uRes, W, H);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, setTex); gl.uniform1i(u.uSet, 0);
      gl.uniform3fv(u.uBase, b.base); gl.uniform3fv(u.uBase2, b.base2);
      gl.uniform4fv(u.uGlow, b.glow); gl.uniform3fv(u.uGlowCol, b.glowCol);
      gl.uniform4fv(u.uGlow2, b.glow2); gl.uniform3fv(u.uGlow2Col, b.glow2Col);
      gl.uniform4fv(u.uBeam, b.beam); gl.uniform4fv(u.uBeamP, b.beamP); gl.uniform3fv(u.uBeamCol, b.beamCol);
      gl.uniform1f(u.uVig, b.vig); gl.uniform1f(u.uFreeze, S.freeze); gl.uniform1f(u.uSetAlpha, S.setAlpha);
      gl.uniform1f(u.uLift, b.lift || 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      // 2. particles (premultiplied, partly additive through the glow term)
      if (nParts > 0) {
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
        gl.useProgram(part.p);
        gl.uniform2f(part.u.uRes, W, H);
        gl.uniform4fv(part.u.uClip, S.clip || [0, 0, W, H]);
        gl.bindVertexArray(pvao);
        gl.bindBuffer(gl.ARRAY_BUFFER, pbuf);
        gl.bufferData(gl.ARRAY_BUFFER, parts.subarray(0, nParts * 12), gl.STREAM_DRAW);
        gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, nParts);
      }
      // 3. post + overlay, accumulate
      gl.bindFramebuffer(gl.FRAMEBUFFER, acc.fb);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ONE);
      gl.useProgram(post.p);
      gl.bindVertexArray(vao);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, scene.tex); gl.uniform1i(post.u.uScene, 0);
      gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, ovTex); gl.uniform1i(post.u.uOv, 1);
      gl.uniform2f(post.u.uRes, W, H);
      gl.uniform4fv(post.u.uRipple, S.ripple);
      gl.uniform1f(post.u.uWeight, weight);
      gl.uniform1f(post.u.uOvAlpha, 1);
      gl.uniform2fv(post.u.uShakeOff, S.shake);
      gl.uniform4fv(post.u.uLens, S.lens || [0, 0, 0, 1]);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.disable(gl.BLEND);
    },
    endFrame(seed, grain, pixels) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, fin.fb);
      gl.viewport(0, 0, W, H);
      gl.useProgram(out.p);
      gl.bindVertexArray(vao);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, acc.tex); gl.uniform1i(out.u.uAcc, 0);
      gl.uniform1f(out.u.uSeed, seed);
      gl.uniform1f(out.u.uGrain, grain);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      // FS_OUT flips vertically, so rows come back top-first.
      if (pixels) gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      // also show on the visible canvas for previews
      gl.bindFramebuffer(gl.READ_FRAMEBUFFER, fin.fb);
      gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, null);
      gl.blitFramebuffer(0, 0, W, H, 0, H, W, 0, gl.COLOR_BUFFER_BIT, gl.NEAREST);
    },
  };
}
