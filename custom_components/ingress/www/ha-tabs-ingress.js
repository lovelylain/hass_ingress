/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const N = globalThis, q = N.ShadowRoot && (N.ShadyCSS === void 0 || N.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, ot = Symbol(), J = /* @__PURE__ */ new WeakMap();
let ft = class {
  constructor(t, e, s) {
    if (this._$cssResult$ = !0, s !== ot) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t, this.t = e;
  }
  get styleSheet() {
    let t = this.o;
    const e = this.t;
    if (q && t === void 0) {
      const s = e !== void 0 && e.length === 1;
      s && (t = J.get(e)), t === void 0 && ((this.o = t = new CSSStyleSheet()).replaceSync(this.cssText), s && J.set(e, t));
    }
    return t;
  }
  toString() {
    return this.cssText;
  }
};
const gt = (r) => new ft(typeof r == "string" ? r : r + "", void 0, ot), mt = (r, t) => {
  if (q) r.adoptedStyleSheets = t.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
  else for (const e of t) {
    const s = document.createElement("style"), i = N.litNonce;
    i !== void 0 && s.setAttribute("nonce", i), s.textContent = e.cssText, r.appendChild(s);
  }
}, K = q ? (r) => r : (r) => r instanceof CSSStyleSheet ? ((t) => {
  let e = "";
  for (const s of t.cssRules) e += s.cssText;
  return gt(e);
})(r) : r;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: At, defineProperty: bt, getOwnPropertyDescriptor: vt, getOwnPropertyNames: yt, getOwnPropertySymbols: wt, getPrototypeOf: Et } = Object, g = globalThis, F = g.trustedTypes, St = F ? F.emptyScript : "", z = g.reactiveElementPolyfillSupport, C = (r, t) => r, W = { toAttribute(r, t) {
  switch (t) {
    case Boolean:
      r = r ? St : null;
      break;
    case Object:
    case Array:
      r = r == null ? r : JSON.stringify(r);
  }
  return r;
}, fromAttribute(r, t) {
  let e = r;
  switch (t) {
    case Boolean:
      e = r !== null;
      break;
    case Number:
      e = r === null ? null : Number(r);
      break;
    case Object:
    case Array:
      try {
        e = JSON.parse(r);
      } catch {
        e = null;
      }
  }
  return e;
} }, nt = (r, t) => !At(r, t), Q = { attribute: !0, type: String, converter: W, reflect: !1, hasChanged: nt };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), g.litPropertyMetadata ?? (g.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
class y extends HTMLElement {
  static addInitializer(t) {
    this._$Ei(), (this.l ?? (this.l = [])).push(t);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t, e = Q) {
    if (e.state && (e.attribute = !1), this._$Ei(), this.elementProperties.set(t, e), !e.noAccessor) {
      const s = Symbol(), i = this.getPropertyDescriptor(t, s, e);
      i !== void 0 && bt(this.prototype, t, i);
    }
  }
  static getPropertyDescriptor(t, e, s) {
    const { get: i, set: o } = vt(this.prototype, t) ?? { get() {
      return this[e];
    }, set(n) {
      this[e] = n;
    } };
    return { get() {
      return i == null ? void 0 : i.call(this);
    }, set(n) {
      const h = i == null ? void 0 : i.call(this);
      o.call(this, n), this.requestUpdate(t, h, s);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(t) {
    return this.elementProperties.get(t) ?? Q;
  }
  static _$Ei() {
    if (this.hasOwnProperty(C("elementProperties"))) return;
    const t = Et(this);
    t.finalize(), t.l !== void 0 && (this.l = [...t.l]), this.elementProperties = new Map(t.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(C("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(C("properties"))) {
      const e = this.properties, s = [...yt(e), ...wt(e)];
      for (const i of s) this.createProperty(i, e[i]);
    }
    const t = this[Symbol.metadata];
    if (t !== null) {
      const e = litPropertyMetadata.get(t);
      if (e !== void 0) for (const [s, i] of e) this.elementProperties.set(s, i);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [e, s] of this.elementProperties) {
      const i = this._$Eu(e, s);
      i !== void 0 && this._$Eh.set(i, e);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(t) {
    const e = [];
    if (Array.isArray(t)) {
      const s = new Set(t.flat(1 / 0).reverse());
      for (const i of s) e.unshift(K(i));
    } else t !== void 0 && e.push(K(t));
    return e;
  }
  static _$Eu(t, e) {
    const s = e.attribute;
    return s === !1 ? void 0 : typeof s == "string" ? s : typeof t == "string" ? t.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    var t;
    this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), (t = this.constructor.l) == null || t.forEach((e) => e(this));
  }
  addController(t) {
    var e;
    (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(t), this.renderRoot !== void 0 && this.isConnected && ((e = t.hostConnected) == null || e.call(t));
  }
  removeController(t) {
    var e;
    (e = this._$EO) == null || e.delete(t);
  }
  _$E_() {
    const t = /* @__PURE__ */ new Map(), e = this.constructor.elementProperties;
    for (const s of e.keys()) this.hasOwnProperty(s) && (t.set(s, this[s]), delete this[s]);
    t.size > 0 && (this._$Ep = t);
  }
  createRenderRoot() {
    const t = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return mt(t, this.constructor.elementStyles), t;
  }
  connectedCallback() {
    var t;
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(!0), (t = this._$EO) == null || t.forEach((e) => {
      var s;
      return (s = e.hostConnected) == null ? void 0 : s.call(e);
    });
  }
  enableUpdating(t) {
  }
  disconnectedCallback() {
    var t;
    (t = this._$EO) == null || t.forEach((e) => {
      var s;
      return (s = e.hostDisconnected) == null ? void 0 : s.call(e);
    });
  }
  attributeChangedCallback(t, e, s) {
    this._$AK(t, s);
  }
  _$EC(t, e) {
    var o;
    const s = this.constructor.elementProperties.get(t), i = this.constructor._$Eu(t, s);
    if (i !== void 0 && s.reflect === !0) {
      const n = (((o = s.converter) == null ? void 0 : o.toAttribute) !== void 0 ? s.converter : W).toAttribute(e, s.type);
      this._$Em = t, n == null ? this.removeAttribute(i) : this.setAttribute(i, n), this._$Em = null;
    }
  }
  _$AK(t, e) {
    var o;
    const s = this.constructor, i = s._$Eh.get(t);
    if (i !== void 0 && this._$Em !== i) {
      const n = s.getPropertyOptions(i), h = typeof n.converter == "function" ? { fromAttribute: n.converter } : ((o = n.converter) == null ? void 0 : o.fromAttribute) !== void 0 ? n.converter : W;
      this._$Em = i, this[i] = h.fromAttribute(e, n.type), this._$Em = null;
    }
  }
  requestUpdate(t, e, s) {
    if (t !== void 0) {
      if (s ?? (s = this.constructor.getPropertyOptions(t)), !(s.hasChanged ?? nt)(this[t], e)) return;
      this.P(t, e, s);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$ET());
  }
  P(t, e, s) {
    this._$AL.has(t) || this._$AL.set(t, e), s.reflect === !0 && this._$Em !== t && (this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Set())).add(t);
  }
  async _$ET() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (e) {
      Promise.reject(e);
    }
    const t = this.scheduleUpdate();
    return t != null && await t, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    var s;
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this._$Ep) {
        for (const [o, n] of this._$Ep) this[o] = n;
        this._$Ep = void 0;
      }
      const i = this.constructor.elementProperties;
      if (i.size > 0) for (const [o, n] of i) n.wrapped !== !0 || this._$AL.has(o) || this[o] === void 0 || this.P(o, this[o], n);
    }
    let t = !1;
    const e = this._$AL;
    try {
      t = this.shouldUpdate(e), t ? (this.willUpdate(e), (s = this._$EO) == null || s.forEach((i) => {
        var o;
        return (o = i.hostUpdate) == null ? void 0 : o.call(i);
      }), this.update(e)) : this._$EU();
    } catch (i) {
      throw t = !1, this._$EU(), i;
    }
    t && this._$AE(e);
  }
  willUpdate(t) {
  }
  _$AE(t) {
    var e;
    (e = this._$EO) == null || e.forEach((s) => {
      var i;
      return (i = s.hostUpdated) == null ? void 0 : i.call(s);
    }), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(t)), this.updated(t);
  }
  _$EU() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t) {
    return !0;
  }
  update(t) {
    this._$Ej && (this._$Ej = this._$Ej.forEach((e) => this._$EC(e, this[e]))), this._$EU();
  }
  updated(t) {
  }
  firstUpdated(t) {
  }
}
y.elementStyles = [], y.shadowRootOptions = { mode: "open" }, y[C("elementProperties")] = /* @__PURE__ */ new Map(), y[C("finalized")] = /* @__PURE__ */ new Map(), z == null || z({ ReactiveElement: y }), (g.reactiveElementVersions ?? (g.reactiveElementVersions = [])).push("2.0.4");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const P = globalThis, R = P.trustedTypes, G = R ? R.createPolicy("lit-html", { createHTML: (r) => r }) : void 0, at = "$lit$", f = `lit$${Math.random().toFixed(9).slice(2)}$`, ht = "?" + f, Ct = `<${ht}>`, v = document, x = () => v.createComment(""), T = (r) => r === null || typeof r != "object" && typeof r != "function", Z = Array.isArray, Pt = (r) => Z(r) || typeof (r == null ? void 0 : r[Symbol.iterator]) == "function", B = `[ 	
\f\r]`, S = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, X = /-->/g, tt = />/g, m = RegExp(`>|${B}(?:([^\\s"'>=/]+)(${B}*=${B}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), et = /'/g, st = /"/g, lt = /^(?:script|style|textarea|title)$/i, Ht = (r) => (t, ...e) => ({ _$litType$: r, strings: t, values: e }), u = Ht(1), w = Symbol.for("lit-noChange"), c = Symbol.for("lit-nothing"), it = /* @__PURE__ */ new WeakMap(), b = v.createTreeWalker(v, 129);
function ct(r, t) {
  if (!Z(r) || !r.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return G !== void 0 ? G.createHTML(t) : t;
}
const xt = (r, t) => {
  const e = r.length - 1, s = [];
  let i, o = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", n = S;
  for (let h = 0; h < e; h++) {
    const a = r[h];
    let d, p, l = -1, $ = 0;
    for (; $ < a.length && (n.lastIndex = $, p = n.exec(a), p !== null); ) $ = n.lastIndex, n === S ? p[1] === "!--" ? n = X : p[1] !== void 0 ? n = tt : p[2] !== void 0 ? (lt.test(p[2]) && (i = RegExp("</" + p[2], "g")), n = m) : p[3] !== void 0 && (n = m) : n === m ? p[0] === ">" ? (n = i ?? S, l = -1) : p[1] === void 0 ? l = -2 : (l = n.lastIndex - p[2].length, d = p[1], n = p[3] === void 0 ? m : p[3] === '"' ? st : et) : n === st || n === et ? n = m : n === X || n === tt ? n = S : (n = m, i = void 0);
    const _ = n === m && r[h + 1].startsWith("/>") ? " " : "";
    o += n === S ? a + Ct : l >= 0 ? (s.push(d), a.slice(0, l) + at + a.slice(l) + f + _) : a + f + (l === -2 ? h : _);
  }
  return [ct(r, o + (r[e] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), s];
};
class U {
  constructor({ strings: t, _$litType$: e }, s) {
    let i;
    this.parts = [];
    let o = 0, n = 0;
    const h = t.length - 1, a = this.parts, [d, p] = xt(t, e);
    if (this.el = U.createElement(d, s), b.currentNode = this.el.content, e === 2 || e === 3) {
      const l = this.el.content.firstChild;
      l.replaceWith(...l.childNodes);
    }
    for (; (i = b.nextNode()) !== null && a.length < h; ) {
      if (i.nodeType === 1) {
        if (i.hasAttributes()) for (const l of i.getAttributeNames()) if (l.endsWith(at)) {
          const $ = p[n++], _ = i.getAttribute(l).split(f), M = /([.?@])?(.*)/.exec($);
          a.push({ type: 1, index: o, name: M[2], strings: _, ctor: M[1] === "." ? Ut : M[1] === "?" ? kt : M[1] === "@" ? Mt : L }), i.removeAttribute(l);
        } else l.startsWith(f) && (a.push({ type: 6, index: o }), i.removeAttribute(l));
        if (lt.test(i.tagName)) {
          const l = i.textContent.split(f), $ = l.length - 1;
          if ($ > 0) {
            i.textContent = R ? R.emptyScript : "";
            for (let _ = 0; _ < $; _++) i.append(l[_], x()), b.nextNode(), a.push({ type: 2, index: ++o });
            i.append(l[$], x());
          }
        }
      } else if (i.nodeType === 8) if (i.data === ht) a.push({ type: 2, index: o });
      else {
        let l = -1;
        for (; (l = i.data.indexOf(f, l + 1)) !== -1; ) a.push({ type: 7, index: o }), l += f.length - 1;
      }
      o++;
    }
  }
  static createElement(t, e) {
    const s = v.createElement("template");
    return s.innerHTML = t, s;
  }
}
function E(r, t, e = r, s) {
  var n, h;
  if (t === w) return t;
  let i = s !== void 0 ? (n = e._$Co) == null ? void 0 : n[s] : e._$Cl;
  const o = T(t) ? void 0 : t._$litDirective$;
  return (i == null ? void 0 : i.constructor) !== o && ((h = i == null ? void 0 : i._$AO) == null || h.call(i, !1), o === void 0 ? i = void 0 : (i = new o(r), i._$AT(r, e, s)), s !== void 0 ? (e._$Co ?? (e._$Co = []))[s] = i : e._$Cl = i), i !== void 0 && (t = E(r, i._$AS(r, t.values), i, s)), t;
}
class Tt {
  constructor(t, e) {
    this._$AV = [], this._$AN = void 0, this._$AD = t, this._$AM = e;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t) {
    const { el: { content: e }, parts: s } = this._$AD, i = ((t == null ? void 0 : t.creationScope) ?? v).importNode(e, !0);
    b.currentNode = i;
    let o = b.nextNode(), n = 0, h = 0, a = s[0];
    for (; a !== void 0; ) {
      if (n === a.index) {
        let d;
        a.type === 2 ? d = new k(o, o.nextSibling, this, t) : a.type === 1 ? d = new a.ctor(o, a.name, a.strings, this, t) : a.type === 6 && (d = new Nt(o, this, t)), this._$AV.push(d), a = s[++h];
      }
      n !== (a == null ? void 0 : a.index) && (o = b.nextNode(), n++);
    }
    return b.currentNode = v, i;
  }
  p(t) {
    let e = 0;
    for (const s of this._$AV) s !== void 0 && (s.strings !== void 0 ? (s._$AI(t, s, e), e += s.strings.length - 2) : s._$AI(t[e])), e++;
  }
}
class k {
  get _$AU() {
    var t;
    return ((t = this._$AM) == null ? void 0 : t._$AU) ?? this._$Cv;
  }
  constructor(t, e, s, i) {
    this.type = 2, this._$AH = c, this._$AN = void 0, this._$AA = t, this._$AB = e, this._$AM = s, this.options = i, this._$Cv = (i == null ? void 0 : i.isConnected) ?? !0;
  }
  get parentNode() {
    let t = this._$AA.parentNode;
    const e = this._$AM;
    return e !== void 0 && (t == null ? void 0 : t.nodeType) === 11 && (t = e.parentNode), t;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t, e = this) {
    t = E(this, t, e), T(t) ? t === c || t == null || t === "" ? (this._$AH !== c && this._$AR(), this._$AH = c) : t !== this._$AH && t !== w && this._(t) : t._$litType$ !== void 0 ? this.$(t) : t.nodeType !== void 0 ? this.T(t) : Pt(t) ? this.k(t) : this._(t);
  }
  O(t) {
    return this._$AA.parentNode.insertBefore(t, this._$AB);
  }
  T(t) {
    this._$AH !== t && (this._$AR(), this._$AH = this.O(t));
  }
  _(t) {
    this._$AH !== c && T(this._$AH) ? this._$AA.nextSibling.data = t : this.T(v.createTextNode(t)), this._$AH = t;
  }
  $(t) {
    var o;
    const { values: e, _$litType$: s } = t, i = typeof s == "number" ? this._$AC(t) : (s.el === void 0 && (s.el = U.createElement(ct(s.h, s.h[0]), this.options)), s);
    if (((o = this._$AH) == null ? void 0 : o._$AD) === i) this._$AH.p(e);
    else {
      const n = new Tt(i, this), h = n.u(this.options);
      n.p(e), this.T(h), this._$AH = n;
    }
  }
  _$AC(t) {
    let e = it.get(t.strings);
    return e === void 0 && it.set(t.strings, e = new U(t)), e;
  }
  k(t) {
    Z(this._$AH) || (this._$AH = [], this._$AR());
    const e = this._$AH;
    let s, i = 0;
    for (const o of t) i === e.length ? e.push(s = new k(this.O(x()), this.O(x()), this, this.options)) : s = e[i], s._$AI(o), i++;
    i < e.length && (this._$AR(s && s._$AB.nextSibling, i), e.length = i);
  }
  _$AR(t = this._$AA.nextSibling, e) {
    var s;
    for ((s = this._$AP) == null ? void 0 : s.call(this, !1, !0, e); t && t !== this._$AB; ) {
      const i = t.nextSibling;
      t.remove(), t = i;
    }
  }
  setConnected(t) {
    var e;
    this._$AM === void 0 && (this._$Cv = t, (e = this._$AP) == null || e.call(this, t));
  }
}
class L {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t, e, s, i, o) {
    this.type = 1, this._$AH = c, this._$AN = void 0, this.element = t, this.name = e, this._$AM = i, this.options = o, s.length > 2 || s[0] !== "" || s[1] !== "" ? (this._$AH = Array(s.length - 1).fill(new String()), this.strings = s) : this._$AH = c;
  }
  _$AI(t, e = this, s, i) {
    const o = this.strings;
    let n = !1;
    if (o === void 0) t = E(this, t, e, 0), n = !T(t) || t !== this._$AH && t !== w, n && (this._$AH = t);
    else {
      const h = t;
      let a, d;
      for (t = o[0], a = 0; a < o.length - 1; a++) d = E(this, h[s + a], e, a), d === w && (d = this._$AH[a]), n || (n = !T(d) || d !== this._$AH[a]), d === c ? t = c : t !== c && (t += (d ?? "") + o[a + 1]), this._$AH[a] = d;
    }
    n && !i && this.j(t);
  }
  j(t) {
    t === c ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t ?? "");
  }
}
class Ut extends L {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t) {
    this.element[this.name] = t === c ? void 0 : t;
  }
}
class kt extends L {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t) {
    this.element.toggleAttribute(this.name, !!t && t !== c);
  }
}
class Mt extends L {
  constructor(t, e, s, i, o) {
    super(t, e, s, i, o), this.type = 5;
  }
  _$AI(t, e = this) {
    if ((t = E(this, t, e, 0) ?? c) === w) return;
    const s = this._$AH, i = t === c && s !== c || t.capture !== s.capture || t.once !== s.once || t.passive !== s.passive, o = t !== c && (s === c || i);
    i && this.element.removeEventListener(this.name, this, s), o && this.element.addEventListener(this.name, this, t), this._$AH = t;
  }
  handleEvent(t) {
    var e;
    typeof this._$AH == "function" ? this._$AH.call(((e = this.options) == null ? void 0 : e.host) ?? this.element, t) : this._$AH.handleEvent(t);
  }
}
class Nt {
  constructor(t, e, s) {
    this.element = t, this.type = 6, this._$AN = void 0, this._$AM = e, this.options = s;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t) {
    E(this, t);
  }
}
const D = P.litHtmlPolyfillSupport;
D == null || D(U, k), (P.litHtmlVersions ?? (P.litHtmlVersions = [])).push("3.2.1");
const dt = (r, t, e) => {
  const s = (e == null ? void 0 : e.renderBefore) ?? t;
  let i = s._$litPart$;
  if (i === void 0) {
    const o = (e == null ? void 0 : e.renderBefore) ?? null;
    s._$litPart$ = i = new k(t.insertBefore(x(), o), o, void 0, e ?? {});
  }
  return i._$AI(r), i;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
let O = class extends y {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    var e;
    const t = super.createRenderRoot();
    return (e = this.renderOptions).renderBefore ?? (e.renderBefore = t.firstChild), t;
  }
  update(t) {
    const e = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t), this._$Do = dt(e, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    var t;
    super.connectedCallback(), (t = this._$Do) == null || t.setConnected(!0);
  }
  disconnectedCallback() {
    var t;
    super.disconnectedCallback(), (t = this._$Do) == null || t.setConnected(!1);
  }
  render() {
    return w;
  }
};
var rt;
O._$litElement$ = !0, O.finalized = !0, (rt = globalThis.litElementHydrateSupport) == null || rt.call(globalThis, { LitElement: O });
const I = globalThis.litElementPolyfillSupport;
I == null || I({ LitElement: O });
(globalThis.litElementVersions ?? (globalThis.litElementVersions = [])).push("4.1.1");
/**
 * @license
 * Copyright 2020 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Ot = (r) => r.strings === void 0;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Rt = { ATTRIBUTE: 1, CHILD: 2, PROPERTY: 3, BOOLEAN_ATTRIBUTE: 4, EVENT: 5, ELEMENT: 6 }, Vt = (r) => (...t) => ({ _$litDirective$: r, values: t });
class Lt {
  constructor(t) {
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AT(t, e, s) {
    this._$Ct = t, this._$AM = e, this._$Ci = s;
  }
  _$AS(t, e) {
    return this.update(t, e);
  }
  update(t, e) {
    return this.render(...e);
  }
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const H = (r, t) => {
  var s;
  const e = r._$AN;
  if (e === void 0) return !1;
  for (const i of e) (s = i._$AO) == null || s.call(i, t, !1), H(i, t);
  return !0;
}, V = (r) => {
  let t, e;
  do {
    if ((t = r._$AM) === void 0) break;
    e = t._$AN, e.delete(r), r = t;
  } while ((e == null ? void 0 : e.size) === 0);
}, pt = (r) => {
  for (let t; t = r._$AM; r = t) {
    let e = t._$AN;
    if (e === void 0) t._$AN = e = /* @__PURE__ */ new Set();
    else if (e.has(r)) break;
    e.add(r), Dt(t);
  }
};
function zt(r) {
  this._$AN !== void 0 ? (V(this), this._$AM = r, pt(this)) : this._$AM = r;
}
function Bt(r, t = !1, e = 0) {
  const s = this._$AH, i = this._$AN;
  if (i !== void 0 && i.size !== 0) if (t) if (Array.isArray(s)) for (let o = e; o < s.length; o++) H(s[o], !1), V(s[o]);
  else s != null && (H(s, !1), V(s));
  else H(this, r);
}
const Dt = (r) => {
  r.type == Rt.CHILD && (r._$AP ?? (r._$AP = Bt), r._$AQ ?? (r._$AQ = zt));
};
class It extends Lt {
  constructor() {
    super(...arguments), this._$AN = void 0;
  }
  _$AT(t, e, s) {
    super._$AT(t, e, s), pt(this), this.isConnected = t._$AU;
  }
  _$AO(t, e = !0) {
    var s, i;
    t !== this.isConnected && (this.isConnected = t, t ? (s = this.reconnected) == null || s.call(this) : (i = this.disconnected) == null || i.call(this)), e && (H(this, t), V(this));
  }
  setValue(t) {
    if (Ot(this._$Ct)) this._$Ct._$AI(t, this);
    else {
      const e = [...this._$Ct._$AH];
      e[this._$Ci] = t, this._$Ct._$AI(e, this, 0);
    }
  }
  disconnected() {
  }
  reconnected() {
  }
}
/**
 * @license
 * Copyright 2020 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const jt = () => new Yt();
class Yt {
}
const j = /* @__PURE__ */ new WeakMap(), Wt = Vt(class extends It {
  render(r) {
    return c;
  }
  update(r, [t]) {
    var s;
    const e = t !== this.Y;
    return e && this.Y !== void 0 && this.rt(void 0), (e || this.lt !== this.ct) && (this.Y = t, this.ht = (s = r.options) == null ? void 0 : s.host, this.rt(this.ct = r.element)), c;
  }
  rt(r) {
    if (this.isConnected || (r = void 0), typeof this.Y == "function") {
      const t = this.ht ?? globalThis;
      let e = j.get(t);
      e === void 0 && (e = /* @__PURE__ */ new WeakMap(), j.set(t, e)), e.get(this.Y) !== void 0 && this.Y.call(this.ht, void 0), e.set(this.Y, r), r !== void 0 && this.Y.call(this.ht, r);
    } else this.Y.value = r;
  }
  get lt() {
    var r, t;
    return typeof this.Y == "function" ? (r = j.get(this.ht ?? globalThis)) == null ? void 0 : r.get(this.Y) : (t = this.Y) == null ? void 0 : t.value;
  }
  disconnected() {
    this.lt === this.ct && this.rt(void 0);
  }
  reconnected() {
    this.rt(this.ct);
  }
});
/**
 * @license
 * Copyright 2018 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const A = (r) => r ?? c;
var qt = "M2,21V19H20V21H2M20,8V5H18V8H20M20,3A2,2 0 0,1 22,5V8A2,2 0 0,1 20,10H18V13A4,4 0 0,1 14,17H8A4,4 0 0,1 4,13V3H20M16,5H6V13A2,2 0 0,0 8,15H14A2,2 0 0,0 16,13V5Z";
const Y = window.__ingressSession, ut = "ha-tabs", $t = "sl-tab-group", Zt = "ha-tab-group", Jt = document.createElement("ha-panel-custom").navigate, Kt = async (r, t, e) => {
  for (let s = 0; s < 2; ++s) {
    for (const i of t)
      if (customElements.get(i))
        return i;
    s === 0 && await r(t[0], e);
  }
  return "";
};
let _t;
class Ft extends HTMLElement {
  setConfig(t) {
    return this.style.height = "100vh", this.attachShadow({ mode: "open" }), this._views = Object.entries(t.children).filter(([, e]) => (e.title || e.icon) && e.ui_mode !== "replace").map(([e, s]) => (s.name = e, s)), this._iframes = this._views.map(() => jt()), this._curView = 0, this._props = {}, this;
  }
  connectedCallback() {
    this._isHassio && Y.init(this._props.hass);
  }
  disconnectedCallback() {
    this._isHassio && Y.fini();
  }
  setProperties(t) {
    if (t.route) {
      const e = (t.route.path || "").split("/", 3)[2], s = this._views.findIndex((i) => i.name === e);
      s >= 0 && (this._curView = s);
    }
    t = Object.assign(this._props, t), dt(this._render(t), this.shadowRoot), this.showPage();
  }
  async showPage(t) {
    var o, n;
    if (t = Number(t ?? this._curView), !(t >= 0 && t < this._views.length))
      return;
    if (t !== this._curView) {
      const h = this._iframes[this._curView].value;
      h.style.display = "none";
    }
    this._curView = t;
    const e = this._views[t], s = this._iframes[t].value;
    if (!s.src) {
      const h = e.url;
      await this._fixAppShow(h), s.src = h;
    }
    s.style.display = "";
    const i = `/_/${e.name}`;
    i !== ((o = this._props.route) == null ? void 0 : o.path) && Jt(`${(n = this._props.route) == null ? void 0 : n.prefix}${i}`);
  }
  async _fixAppShow(t) {
    let e = new URL(t, location.origin);
    if (e.origin === location.origin) {
      if (!this._isHassio && e.pathname.startsWith("/api/hassio_ingress/")) {
        await Y.init(this._props.hass), this._isHassio = !0;
        return;
      } else if (!e.pathname.startsWith("/api/ingress/")) return;
      try {
        if (!window.externalApp && !window.webkit) return;
        const s = await fetch(e.href);
        if (!s.ok || !s.redirected || (e = new URL(s.url), e.origin !== location.origin || !e.searchParams.has("replace"))) return;
        const i = document.createElement("partial-panel-resolver");
        i.hass = this._props.hass, i.route = { prefix: "", path: e.pathname };
        const o = this.shadowRoot;
        o.appendChild(i), await new Promise((n) => setTimeout(n, 1e3)), o.removeChild(i);
      } catch {
      }
    }
  }
  _render(t) {
    switch (_t) {
      case ut:
        return this._render1(t);
      case $t:
        return this._render2(t);
      default:
        return this._render3(t);
    }
  }
  _render1(t) {
    return u`<style>
        ha-tabs {
          --paper-tabs-selection-bar-color: var(
            --app-header-selection-bar-color,
            var(--app-header-text-color, #fff)
          );
          text-transform: uppercase;
        }
        iframe {
          border: 0;
          width: 100%;
          height: 100%;
          background-color: var(--primary-background-color);
        }
      </style>
      <hass-subpage main-page .hass=${t.hass} .narrow=${t.narrow}>
        <ha-tabs
          slot="header"
          scrollable
          .selected=${this._curView}
          @iron-activate=${(e) => this.showPage(e.detail.selected)}
        >
          ${this._views.map(
      (e) => u`<paper-tab aria-label=${A(e.title)}>
                ${e.icon ? u`<ha-icon title=${A(e.title)} .icon=${e.icon}></ha-icon>` : e.title || ""}
              </paper-tab>`
    )}
        </ha-tabs>
        ${this._render_iframes()}
      </hass-subpage>`;
  }
  _render_iframes() {
    return u`<a
        slot="toolbar-icon"
        href="https://buymeacoffee.com/lovelylain"
        target="_blank"
        rel="noreferrer"
      >
        <ha-icon-button .label=${"Donate"} .path=${qt}></ha-icon-button>
      </a>
      ${this._views.map(
      (t, e) => u`<iframe
            ${Wt(this._iframes[e])}
            title=${A(t.title)}
            style="display: none;"
            allow="fullscreen"
          ></iframe>`
    )}`;
  }
  _render2(t) {
    return u`<style>
        sl-tab-group {
          --ha-tab-indicator-color: var(
            --app-header-selection-bar-color,
            var(--app-header-text-color, white)
          );
          --ha-tab-active-text-color: var(--app-header-text-color, white);
          --ha-tab-track-color: transparent;
          align-self: flex-end;
          flex-grow: 1;
          min-width: 0;
          height: 100%;
        }
        sl-tab-group::part(nav) {
          padding: 0;
        }
        sl-tab-group::part(scroll-button) {
          background-color: var(--app-header-background-color);
          background: linear-gradient(90deg, var(--app-header-background-color), transparent);
          z-index: 1;
        }
        sl-tab-group::part(scroll-button--end) {
          background: linear-gradient(270deg, var(--app-header-background-color), transparent);
        }
        iframe {
          border: 0;
          width: 100%;
          height: 100%;
          background-color: var(--primary-background-color);
        }
      </style>
      <hass-subpage main-page .hass=${t.hass} .narrow=${t.narrow}>
        <sl-tab-group slot="header" @sl-tab-show=${(e) => this.showPage(e.detail.name)}>
          ${this._views.map(
      (e, s) => u`<sl-tab
              slot="nav"
              aria-label=${A(e.title)}
              panel=${s}
              .active=${this._curView === s}
            >
              ${e.icon ? u`<ha-icon title=${A(e.title)} .icon=${e.icon}></ha-icon>` : e.title || ""}
            </sl-tab>`
    )}
        </sl-tab-group>
        ${this._render_iframes()}
      </hass-subpage>`;
  }
  _render3(t) {
    return u`<style>
        ha-tab-group {
          --ha-tab-indicator-color: var(
            --app-header-selection-bar-color,
            var(--app-header-text-color, white)
          );
          --ha-tab-active-text-color: var(--app-header-text-color, white);
          --ha-tab-track-color: transparent;
          align-self: flex-end;
          flex-grow: 1;
          min-width: 0;
          height: 100%;
        }
        ha-tab-group::part(nav) {
          padding: 0;
        }
        ha-tab-group::part(scroll-button) {
          background-color: var(--app-header-background-color);
          background: linear-gradient(90deg, var(--app-header-background-color), transparent);
          z-index: 1;
        }
        ha-tab-group::part(scroll-button--end) {
          background: linear-gradient(270deg, var(--app-header-background-color), transparent);
        }
        iframe {
          border: 0;
          width: 100%;
          height: 100%;
          background-color: var(--primary-background-color);
        }
      </style>
      <hass-subpage main-page .hass=${t.hass} .narrow=${t.narrow}>
        <ha-tab-group slot="header" @wa-tab-show=${(e) => this.showPage(e.detail.name)}>
          ${this._views.map(
      (e, s) => u`<ha-tab-group-tab
              slot="nav"
              aria-label=${A(e.title)}
              panel=${s}
              .active=${this._curView === s}
            >
              ${e.icon ? u`<ha-icon title=${A(e.title)} .icon=${e.icon}></ha-icon>` : e.title || ""}
            </ha-tab-group-tab>`
    )}
        </ha-tab-group>
        ${this._render_iframes()}
      </hass-subpage>`;
  }
}
customElements.define("ha-tabs-ingress", Ft);
const Xt = async (r) => {
  const { ensureHaElem: t } = r;
  return await t("hass-subpage", "iframe"), _t = await Kt(
    t,
    [Zt, $t, ut],
    "lovelace"
  ), document.createElement("ha-tabs-ingress").setConfig(r);
};
export {
  Xt as default
};
