const pe = (t, r) => {
  document.createElement("ha-panel-custom").navigate(t, r);
}, ve = async (t) => {
  if (!customElements.get(`ha-panel-${t}`)) {
    const r = [{ url_path: "tmp", component_name: "iframe" }];
    await document.createElement("partial-panel-resolver").getRoutes(r).routes.tmp.load();
  }
};
var V = function(t, r) {
  return V = Object.setPrototypeOf || { __proto__: [] } instanceof Array && function(e, n) {
    e.__proto__ = n;
  } || function(e, n) {
    for (var i in n) Object.prototype.hasOwnProperty.call(n, i) && (e[i] = n[i]);
  }, V(t, r);
};
function E(t, r) {
  if (typeof r != "function" && r !== null)
    throw new TypeError("Class extends value " + String(r) + " is not a constructor or null");
  V(t, r);
  function e() {
    this.constructor = t;
  }
  t.prototype = r === null ? Object.create(r) : (e.prototype = r.prototype, new e());
}
function ye(t, r, e, n) {
  function i(o) {
    return o instanceof e ? o : new e(function(s) {
      s(o);
    });
  }
  return new (e || (e = Promise))(function(o, s) {
    function c(l) {
      try {
        a(n.next(l));
      } catch (d) {
        s(d);
      }
    }
    function u(l) {
      try {
        a(n.throw(l));
      } catch (d) {
        s(d);
      }
    }
    function a(l) {
      l.done ? o(l.value) : i(l.value).then(c, u);
    }
    a((n = n.apply(t, r || [])).next());
  });
}
function N(t, r) {
  var e = { label: 0, sent: function() {
    if (o[0] & 1) throw o[1];
    return o[1];
  }, trys: [], ops: [] }, n, i, o, s;
  return s = { next: c(0), throw: c(1), return: c(2) }, typeof Symbol == "function" && (s[Symbol.iterator] = function() {
    return this;
  }), s;
  function c(a) {
    return function(l) {
      return u([a, l]);
    };
  }
  function u(a) {
    if (n) throw new TypeError("Generator is already executing.");
    for (; s && (s = 0, a[0] && (e = 0)), e; ) try {
      if (n = 1, i && (o = a[0] & 2 ? i.return : a[0] ? i.throw || ((o = i.return) && o.call(i), 0) : i.next) && !(o = o.call(i, a[1])).done) return o;
      switch (i = 0, o && (a = [a[0] & 2, o.value]), a[0]) {
        case 0:
        case 1:
          o = a;
          break;
        case 4:
          return e.label++, { value: a[1], done: !1 };
        case 5:
          e.label++, i = a[1], a = [0];
          continue;
        case 7:
          a = e.ops.pop(), e.trys.pop();
          continue;
        default:
          if (o = e.trys, !(o = o.length > 0 && o[o.length - 1]) && (a[0] === 6 || a[0] === 2)) {
            e = 0;
            continue;
          }
          if (a[0] === 3 && (!o || a[1] > o[0] && a[1] < o[3])) {
            e.label = a[1];
            break;
          }
          if (a[0] === 6 && e.label < o[1]) {
            e.label = o[1], o = a;
            break;
          }
          if (o && e.label < o[2]) {
            e.label = o[2], e.ops.push(a);
            break;
          }
          o[2] && e.ops.pop(), e.trys.pop();
          continue;
      }
      a = r.call(t, e);
    } catch (l) {
      a = [6, l], i = 0;
    } finally {
      n = o = 0;
    }
    if (a[0] & 5) throw a[1];
    return { value: a[0] ? a[1] : void 0, done: !0 };
  }
}
function S(t) {
  var r = typeof Symbol == "function" && Symbol.iterator, e = r && t[r], n = 0;
  if (e) return e.call(t);
  if (t && typeof t.length == "number") return {
    next: function() {
      return t && n >= t.length && (t = void 0), { value: t && t[n++], done: !t };
    }
  };
  throw new TypeError(r ? "Object is not iterable." : "Symbol.iterator is not defined.");
}
function A(t, r) {
  var e = typeof Symbol == "function" && t[Symbol.iterator];
  if (!e) return t;
  var n = e.call(t), i, o = [], s;
  try {
    for (; (r === void 0 || r-- > 0) && !(i = n.next()).done; ) o.push(i.value);
  } catch (c) {
    s = { error: c };
  } finally {
    try {
      i && !i.done && (e = n.return) && e.call(n);
    } finally {
      if (s) throw s.error;
    }
  }
  return o;
}
function H(t, r, e) {
  if (e || arguments.length === 2) for (var n = 0, i = r.length, o; n < i; n++)
    (o || !(n in r)) && (o || (o = Array.prototype.slice.call(r, 0, n)), o[n] = r[n]);
  return t.concat(o || Array.prototype.slice.call(r));
}
function _(t) {
  return this instanceof _ ? (this.v = t, this) : new _(t);
}
function be(t, r, e) {
  if (!Symbol.asyncIterator) throw new TypeError("Symbol.asyncIterator is not defined.");
  var n = e.apply(t, r || []), i, o = [];
  return i = {}, c("next"), c("throw"), c("return", s), i[Symbol.asyncIterator] = function() {
    return this;
  }, i;
  function s(f) {
    return function(v) {
      return Promise.resolve(v).then(f, d);
    };
  }
  function c(f, v) {
    n[f] && (i[f] = function(p) {
      return new Promise(function(k, x) {
        o.push([f, p, k, x]) > 1 || u(f, p);
      });
    }, v && (i[f] = v(i[f])));
  }
  function u(f, v) {
    try {
      a(n[f](v));
    } catch (p) {
      y(o[0][3], p);
    }
  }
  function a(f) {
    f.value instanceof _ ? Promise.resolve(f.value.v).then(l, d) : y(o[0][2], f);
  }
  function l(f) {
    u("next", f);
  }
  function d(f) {
    u("throw", f);
  }
  function y(f, v) {
    f(v), o.shift(), o.length && u(o[0][0], o[0][1]);
  }
}
function me(t) {
  if (!Symbol.asyncIterator) throw new TypeError("Symbol.asyncIterator is not defined.");
  var r = t[Symbol.asyncIterator], e;
  return r ? r.call(t) : (t = typeof S == "function" ? S(t) : t[Symbol.iterator](), e = {}, n("next"), n("throw"), n("return"), e[Symbol.asyncIterator] = function() {
    return this;
  }, e);
  function n(o) {
    e[o] = t[o] && function(s) {
      return new Promise(function(c, u) {
        s = t[o](s), i(c, u, s.done, s.value);
      });
    };
  }
  function i(o, s, c, u) {
    Promise.resolve(u).then(function(a) {
      o({ value: a, done: c });
    }, s);
  }
}
function h(t) {
  return typeof t == "function";
}
function ee(t) {
  var r = function(n) {
    Error.call(n), n.stack = new Error().stack;
  }, e = t(r);
  return e.prototype = Object.create(Error.prototype), e.prototype.constructor = e, e;
}
var L = ee(function(t) {
  return function(e) {
    t(this), this.message = e ? e.length + ` errors occurred during unsubscription:
` + e.map(function(n, i) {
      return i + 1 + ") " + n.toString();
    }).join(`
  `) : "", this.name = "UnsubscriptionError", this.errors = e;
  };
});
function F(t, r) {
  if (t) {
    var e = t.indexOf(r);
    0 <= e && t.splice(e, 1);
  }
}
var M = function() {
  function t(r) {
    this.initialTeardown = r, this.closed = !1, this._parentage = null, this._finalizers = null;
  }
  return t.prototype.unsubscribe = function() {
    var r, e, n, i, o;
    if (!this.closed) {
      this.closed = !0;
      var s = this._parentage;
      if (s)
        if (this._parentage = null, Array.isArray(s))
          try {
            for (var c = S(s), u = c.next(); !u.done; u = c.next()) {
              var a = u.value;
              a.remove(this);
            }
          } catch (p) {
            r = { error: p };
          } finally {
            try {
              u && !u.done && (e = c.return) && e.call(c);
            } finally {
              if (r) throw r.error;
            }
          }
        else
          s.remove(this);
      var l = this.initialTeardown;
      if (h(l))
        try {
          l();
        } catch (p) {
          o = p instanceof L ? p.errors : [p];
        }
      var d = this._finalizers;
      if (d) {
        this._finalizers = null;
        try {
          for (var y = S(d), f = y.next(); !f.done; f = y.next()) {
            var v = f.value;
            try {
              W(v);
            } catch (p) {
              o = o ?? [], p instanceof L ? o = H(H([], A(o)), A(p.errors)) : o.push(p);
            }
          }
        } catch (p) {
          n = { error: p };
        } finally {
          try {
            f && !f.done && (i = y.return) && i.call(y);
          } finally {
            if (n) throw n.error;
          }
        }
      }
      if (o)
        throw new L(o);
    }
  }, t.prototype.add = function(r) {
    var e;
    if (r && r !== this)
      if (this.closed)
        W(r);
      else {
        if (r instanceof t) {
          if (r.closed || r._hasParent(this))
            return;
          r._addParent(this);
        }
        (this._finalizers = (e = this._finalizers) !== null && e !== void 0 ? e : []).push(r);
      }
  }, t.prototype._hasParent = function(r) {
    var e = this._parentage;
    return e === r || Array.isArray(e) && e.includes(r);
  }, t.prototype._addParent = function(r) {
    var e = this._parentage;
    this._parentage = Array.isArray(e) ? (e.push(r), e) : e ? [e, r] : r;
  }, t.prototype._removeParent = function(r) {
    var e = this._parentage;
    e === r ? this._parentage = null : Array.isArray(e) && F(e, r);
  }, t.prototype.remove = function(r) {
    var e = this._finalizers;
    e && F(e, r), r instanceof t && r._removeParent(this);
  }, t.EMPTY = function() {
    var r = new t();
    return r.closed = !0, r;
  }(), t;
}(), te = M.EMPTY;
function re(t) {
  return t instanceof M || t && "closed" in t && h(t.remove) && h(t.add) && h(t.unsubscribe);
}
function W(t) {
  h(t) ? t() : t.unsubscribe();
}
var ne = {
  onUnhandledError: null,
  onStoppedNotification: null,
  Promise: void 0,
  useDeprecatedSynchronousErrorHandling: !1,
  useDeprecatedNextContext: !1
}, oe = {
  setTimeout: function(t, r) {
    for (var e = [], n = 2; n < arguments.length; n++)
      e[n - 2] = arguments[n];
    return setTimeout.apply(void 0, H([t, r], A(e)));
  },
  clearTimeout: function(t) {
    var r = oe.delegate;
    return ((r == null ? void 0 : r.clearTimeout) || clearTimeout)(t);
  },
  delegate: void 0
};
function ie(t) {
  oe.setTimeout(function() {
    throw t;
  });
}
function B() {
}
function $(t) {
  t();
}
var z = function(t) {
  E(r, t);
  function r(e) {
    var n = t.call(this) || this;
    return n.isStopped = !1, e ? (n.destination = e, re(e) && e.add(n)) : n.destination = _e, n;
  }
  return r.create = function(e, n, i) {
    return new Y(e, n, i);
  }, r.prototype.next = function(e) {
    this.isStopped || this._next(e);
  }, r.prototype.error = function(e) {
    this.isStopped || (this.isStopped = !0, this._error(e));
  }, r.prototype.complete = function() {
    this.isStopped || (this.isStopped = !0, this._complete());
  }, r.prototype.unsubscribe = function() {
    this.closed || (this.isStopped = !0, t.prototype.unsubscribe.call(this), this.destination = null);
  }, r.prototype._next = function(e) {
    this.destination.next(e);
  }, r.prototype._error = function(e) {
    try {
      this.destination.error(e);
    } finally {
      this.unsubscribe();
    }
  }, r.prototype._complete = function() {
    try {
      this.destination.complete();
    } finally {
      this.unsubscribe();
    }
  }, r;
}(M), we = Function.prototype.bind;
function R(t, r) {
  return we.call(t, r);
}
var ge = function() {
  function t(r) {
    this.partialObserver = r;
  }
  return t.prototype.next = function(r) {
    var e = this.partialObserver;
    if (e.next)
      try {
        e.next(r);
      } catch (n) {
        j(n);
      }
  }, t.prototype.error = function(r) {
    var e = this.partialObserver;
    if (e.error)
      try {
        e.error(r);
      } catch (n) {
        j(n);
      }
    else
      j(r);
  }, t.prototype.complete = function() {
    var r = this.partialObserver;
    if (r.complete)
      try {
        r.complete();
      } catch (e) {
        j(e);
      }
  }, t;
}(), Y = function(t) {
  E(r, t);
  function r(e, n, i) {
    var o = t.call(this) || this, s;
    if (h(e) || !e)
      s = {
        next: e ?? void 0,
        error: n ?? void 0,
        complete: i ?? void 0
      };
    else {
      var c;
      o && ne.useDeprecatedNextContext ? (c = Object.create(e), c.unsubscribe = function() {
        return o.unsubscribe();
      }, s = {
        next: e.next && R(e.next, c),
        error: e.error && R(e.error, c),
        complete: e.complete && R(e.complete, c)
      }) : s = e;
    }
    return o.destination = new ge(s), o;
  }
  return r;
}(z);
function j(t) {
  ie(t);
}
function Se(t) {
  throw t;
}
var _e = {
  closed: !0,
  next: B,
  error: Se,
  complete: B
}, D = function() {
  return typeof Symbol == "function" && Symbol.observable || "@@observable";
}();
function se(t) {
  return t;
}
function Ee(t) {
  return t.length === 0 ? se : t.length === 1 ? t[0] : function(e) {
    return t.reduce(function(n, i) {
      return i(n);
    }, e);
  };
}
var b = function() {
  function t(r) {
    r && (this._subscribe = r);
  }
  return t.prototype.lift = function(r) {
    var e = new t();
    return e.source = this, e.operator = r, e;
  }, t.prototype.subscribe = function(r, e, n) {
    var i = this, o = Pe(r) ? r : new Y(r, e, n);
    return $(function() {
      var s = i, c = s.operator, u = s.source;
      o.add(c ? c.call(o, u) : u ? i._subscribe(o) : i._trySubscribe(o));
    }), o;
  }, t.prototype._trySubscribe = function(r) {
    try {
      return this._subscribe(r);
    } catch (e) {
      r.error(e);
    }
  }, t.prototype.forEach = function(r, e) {
    var n = this;
    return e = K(e), new e(function(i, o) {
      var s = new Y({
        next: function(c) {
          try {
            r(c);
          } catch (u) {
            o(u), s.unsubscribe();
          }
        },
        error: o,
        complete: i
      });
      n.subscribe(s);
    });
  }, t.prototype._subscribe = function(r) {
    var e;
    return (e = this.source) === null || e === void 0 ? void 0 : e.subscribe(r);
  }, t.prototype[D] = function() {
    return this;
  }, t.prototype.pipe = function() {
    for (var r = [], e = 0; e < arguments.length; e++)
      r[e] = arguments[e];
    return Ee(r)(this);
  }, t.prototype.toPromise = function(r) {
    var e = this;
    return r = K(r), new r(function(n, i) {
      var o;
      e.subscribe(function(s) {
        return o = s;
      }, function(s) {
        return i(s);
      }, function() {
        return n(o);
      });
    });
  }, t.create = function(r) {
    return new t(r);
  }, t;
}();
function K(t) {
  var r;
  return (r = t ?? ne.Promise) !== null && r !== void 0 ? r : Promise;
}
function xe(t) {
  return t && h(t.next) && h(t.error) && h(t.complete);
}
function Pe(t) {
  return t && t instanceof z || xe(t) && re(t);
}
function Ie(t) {
  return h(t == null ? void 0 : t.lift);
}
function w(t) {
  return function(r) {
    if (Ie(r))
      return r.lift(function(e) {
        try {
          return t(e, this);
        } catch (n) {
          this.error(n);
        }
      });
    throw new TypeError("Unable to lift unknown Observable type");
  };
}
function m(t, r, e, n, i) {
  return new Ae(t, r, e, n, i);
}
var Ae = function(t) {
  E(r, t);
  function r(e, n, i, o, s, c) {
    var u = t.call(this, e) || this;
    return u.onFinalize = s, u.shouldUnsubscribe = c, u._next = n ? function(a) {
      try {
        n(a);
      } catch (l) {
        e.error(l);
      }
    } : t.prototype._next, u._error = o ? function(a) {
      try {
        o(a);
      } catch (l) {
        e.error(l);
      } finally {
        this.unsubscribe();
      }
    } : t.prototype._error, u._complete = i ? function() {
      try {
        i();
      } catch (a) {
        e.error(a);
      } finally {
        this.unsubscribe();
      }
    } : t.prototype._complete, u;
  }
  return r.prototype.unsubscribe = function() {
    var e;
    if (!this.shouldUnsubscribe || this.shouldUnsubscribe()) {
      var n = this.closed;
      t.prototype.unsubscribe.call(this), !n && ((e = this.onFinalize) === null || e === void 0 || e.call(this));
    }
  }, r;
}(z), Te = ee(function(t) {
  return function() {
    t(this), this.name = "ObjectUnsubscribedError", this.message = "object unsubscribed";
  };
}), ae = function(t) {
  E(r, t);
  function r() {
    var e = t.call(this) || this;
    return e.closed = !1, e.currentObservers = null, e.observers = [], e.isStopped = !1, e.hasError = !1, e.thrownError = null, e;
  }
  return r.prototype.lift = function(e) {
    var n = new Q(this, this);
    return n.operator = e, n;
  }, r.prototype._throwIfClosed = function() {
    if (this.closed)
      throw new Te();
  }, r.prototype.next = function(e) {
    var n = this;
    $(function() {
      var i, o;
      if (n._throwIfClosed(), !n.isStopped) {
        n.currentObservers || (n.currentObservers = Array.from(n.observers));
        try {
          for (var s = S(n.currentObservers), c = s.next(); !c.done; c = s.next()) {
            var u = c.value;
            u.next(e);
          }
        } catch (a) {
          i = { error: a };
        } finally {
          try {
            c && !c.done && (o = s.return) && o.call(s);
          } finally {
            if (i) throw i.error;
          }
        }
      }
    });
  }, r.prototype.error = function(e) {
    var n = this;
    $(function() {
      if (n._throwIfClosed(), !n.isStopped) {
        n.hasError = n.isStopped = !0, n.thrownError = e;
        for (var i = n.observers; i.length; )
          i.shift().error(e);
      }
    });
  }, r.prototype.complete = function() {
    var e = this;
    $(function() {
      if (e._throwIfClosed(), !e.isStopped) {
        e.isStopped = !0;
        for (var n = e.observers; n.length; )
          n.shift().complete();
      }
    });
  }, r.prototype.unsubscribe = function() {
    this.isStopped = this.closed = !0, this.observers = this.currentObservers = null;
  }, Object.defineProperty(r.prototype, "observed", {
    get: function() {
      var e;
      return ((e = this.observers) === null || e === void 0 ? void 0 : e.length) > 0;
    },
    enumerable: !1,
    configurable: !0
  }), r.prototype._trySubscribe = function(e) {
    return this._throwIfClosed(), t.prototype._trySubscribe.call(this, e);
  }, r.prototype._subscribe = function(e) {
    return this._throwIfClosed(), this._checkFinalizedStatuses(e), this._innerSubscribe(e);
  }, r.prototype._innerSubscribe = function(e) {
    var n = this, i = this, o = i.hasError, s = i.isStopped, c = i.observers;
    return o || s ? te : (this.currentObservers = null, c.push(e), new M(function() {
      n.currentObservers = null, F(c, e);
    }));
  }, r.prototype._checkFinalizedStatuses = function(e) {
    var n = this, i = n.hasError, o = n.thrownError, s = n.isStopped;
    i ? e.error(o) : s && e.complete();
  }, r.prototype.asObservable = function() {
    var e = new b();
    return e.source = this, e;
  }, r.create = function(e, n) {
    return new Q(e, n);
  }, r;
}(b), Q = function(t) {
  E(r, t);
  function r(e, n) {
    var i = t.call(this) || this;
    return i.destination = e, i.source = n, i;
  }
  return r.prototype.next = function(e) {
    var n, i;
    (i = (n = this.destination) === null || n === void 0 ? void 0 : n.next) === null || i === void 0 || i.call(n, e);
  }, r.prototype.error = function(e) {
    var n, i;
    (i = (n = this.destination) === null || n === void 0 ? void 0 : n.error) === null || i === void 0 || i.call(n, e);
  }, r.prototype.complete = function() {
    var e, n;
    (n = (e = this.destination) === null || e === void 0 ? void 0 : e.complete) === null || n === void 0 || n.call(e);
  }, r.prototype._subscribe = function(e) {
    var n, i;
    return (i = (n = this.source) === null || n === void 0 ? void 0 : n.subscribe(e)) !== null && i !== void 0 ? i : te;
  }, r;
}(ae), Oe = function(t) {
  E(r, t);
  function r(e) {
    var n = t.call(this) || this;
    return n._value = e, n;
  }
  return Object.defineProperty(r.prototype, "value", {
    get: function() {
      return this.getValue();
    },
    enumerable: !1,
    configurable: !0
  }), r.prototype._subscribe = function(e) {
    var n = t.prototype._subscribe.call(this, e);
    return !n.closed && e.next(this._value), n;
  }, r.prototype.getValue = function() {
    var e = this, n = e.hasError, i = e.thrownError, o = e._value;
    if (n)
      throw i;
    return this._throwIfClosed(), o;
  }, r.prototype.next = function(e) {
    t.prototype.next.call(this, this._value = e);
  }, r;
}(ae), ue = new b(function(t) {
  return t.complete();
}), ce = function(t) {
  return t && typeof t.length == "number" && typeof t != "function";
};
function ke(t) {
  return h(t == null ? void 0 : t.then);
}
function je(t) {
  return h(t[D]);
}
function $e(t) {
  return Symbol.asyncIterator && h(t == null ? void 0 : t[Symbol.asyncIterator]);
}
function Ue(t) {
  return new TypeError("You provided " + (t !== null && typeof t == "object" ? "an invalid object" : "'" + t + "'") + " where a stream was expected. You can provide an Observable, Promise, ReadableStream, Array, AsyncIterable, or Iterable.");
}
function He() {
  return typeof Symbol != "function" || !Symbol.iterator ? "@@iterator" : Symbol.iterator;
}
var Me = He();
function Ce(t) {
  return h(t == null ? void 0 : t[Me]);
}
function Le(t) {
  return be(this, arguments, function() {
    var e, n, i, o;
    return N(this, function(s) {
      switch (s.label) {
        case 0:
          e = t.getReader(), s.label = 1;
        case 1:
          s.trys.push([1, , 9, 10]), s.label = 2;
        case 2:
          return [4, _(e.read())];
        case 3:
          return n = s.sent(), i = n.value, o = n.done, o ? [4, _(void 0)] : [3, 5];
        case 4:
          return [2, s.sent()];
        case 5:
          return [4, _(i)];
        case 6:
          return [4, s.sent()];
        case 7:
          return s.sent(), [3, 2];
        case 8:
          return [3, 10];
        case 9:
          return e.releaseLock(), [7];
        case 10:
          return [2];
      }
    });
  });
}
function Re(t) {
  return h(t == null ? void 0 : t.getReader);
}
function O(t) {
  if (t instanceof b)
    return t;
  if (t != null) {
    if (je(t))
      return Ve(t);
    if (ce(t))
      return Fe(t);
    if (ke(t))
      return Be(t);
    if ($e(t))
      return le(t);
    if (Ce(t))
      return Ye(t);
    if (Re(t))
      return qe(t);
  }
  throw Ue(t);
}
function Ve(t) {
  return new b(function(r) {
    var e = t[D]();
    if (h(e.subscribe))
      return e.subscribe(r);
    throw new TypeError("Provided object does not correctly implement Symbol.observable");
  });
}
function Fe(t) {
  return new b(function(r) {
    for (var e = 0; e < t.length && !r.closed; e++)
      r.next(t[e]);
    r.complete();
  });
}
function Be(t) {
  return new b(function(r) {
    t.then(function(e) {
      r.closed || (r.next(e), r.complete());
    }, function(e) {
      return r.error(e);
    }).then(null, ie);
  });
}
function Ye(t) {
  return new b(function(r) {
    var e, n;
    try {
      for (var i = S(t), o = i.next(); !o.done; o = i.next()) {
        var s = o.value;
        if (r.next(s), r.closed)
          return;
      }
    } catch (c) {
      e = { error: c };
    } finally {
      try {
        o && !o.done && (n = i.return) && n.call(i);
      } finally {
        if (e) throw e.error;
      }
    }
    r.complete();
  });
}
function le(t) {
  return new b(function(r) {
    ze(t, r).catch(function(e) {
      return r.error(e);
    });
  });
}
function qe(t) {
  return le(Le(t));
}
function ze(t, r) {
  var e, n, i, o;
  return ye(this, void 0, void 0, function() {
    var s, c;
    return N(this, function(u) {
      switch (u.label) {
        case 0:
          u.trys.push([0, 5, 6, 11]), e = me(t), u.label = 1;
        case 1:
          return [4, e.next()];
        case 2:
          if (n = u.sent(), !!n.done) return [3, 4];
          if (s = n.value, r.next(s), r.closed)
            return [2];
          u.label = 3;
        case 3:
          return [3, 1];
        case 4:
          return [3, 11];
        case 5:
          return c = u.sent(), i = { error: c }, [3, 11];
        case 6:
          return u.trys.push([6, , 9, 10]), n && !n.done && (o = e.return) ? [4, o.call(e)] : [3, 8];
        case 7:
          u.sent(), u.label = 8;
        case 8:
          return [3, 10];
        case 9:
          if (i) throw i.error;
          return [7];
        case 10:
          return [7];
        case 11:
          return r.complete(), [2];
      }
    });
  });
}
function T(t, r) {
  return w(function(e, n) {
    var i = 0;
    e.subscribe(m(n, function(o) {
      n.next(t.call(r, o, i++));
    }));
  });
}
var De = Array.isArray;
function Ge(t, r) {
  return De(r) ? t.apply(void 0, H([], A(r))) : t(r);
}
function We(t) {
  return T(function(r) {
    return Ge(t, r);
  });
}
function Ke(t, r, e, n, i, o, s, c) {
  var u = [], a = 0, l = 0, d = !1, y = function() {
    d && !u.length && !a && r.complete();
  }, f = function(p) {
    return a < n ? v(p) : u.push(p);
  }, v = function(p) {
    a++;
    var k = !1;
    O(e(p, l++)).subscribe(m(r, function(x) {
      r.next(x);
    }, function() {
      k = !0;
    }, void 0, function() {
      if (k)
        try {
          a--;
          for (var x = function() {
            var C = u.shift();
            s || v(C);
          }; u.length && a < n; )
            x();
          y();
        } catch (C) {
          r.error(C);
        }
    }));
  };
  return t.subscribe(m(r, f, function() {
    d = !0, y();
  })), function() {
  };
}
function fe(t, r, e) {
  return e === void 0 && (e = 1 / 0), h(r) ? fe(function(n, i) {
    return T(function(o, s) {
      return r(n, o, i, s);
    })(O(t(n, i)));
  }, e) : (typeof r == "number" && (e = r), w(function(n, i) {
    return Ke(n, i, t, e);
  }));
}
var Qe = ["addListener", "removeListener"], Je = ["addEventListener", "removeEventListener"], Xe = ["on", "off"];
function g(t, r, e, n) {
  if (h(e) && (n = e, e = void 0), n)
    return g(t, r, e).pipe(We(n));
  var i = A(et(t) ? Je.map(function(c) {
    return function(u) {
      return t[c](r, u, e);
    };
  }) : Ze(t) ? Qe.map(J(t, r)) : Ne(t) ? Xe.map(J(t, r)) : [], 2), o = i[0], s = i[1];
  if (!o && ce(t))
    return fe(function(c) {
      return g(c, r, e);
    })(O(t));
  if (!o)
    throw new TypeError("Invalid event target");
  return new b(function(c) {
    var u = function() {
      for (var a = [], l = 0; l < arguments.length; l++)
        a[l] = arguments[l];
      return c.next(1 < a.length ? a : a[0]);
    };
    return o(u), function() {
      return s(u);
    };
  });
}
function J(t, r) {
  return function(e) {
    return function(n) {
      return t[e](r, n);
    };
  };
}
function Ze(t) {
  return h(t.addListener) && h(t.removeListener);
}
function Ne(t) {
  return h(t.on) && h(t.off);
}
function et(t) {
  return h(t.addEventListener) && h(t.removeEventListener);
}
function P(t, r) {
  return w(function(e, n) {
    var i = 0;
    e.subscribe(m(n, function(o) {
      return t.call(r, o, i++) && n.next(o);
    }));
  });
}
function he(t) {
  return t <= 0 ? function() {
    return ue;
  } : w(function(r, e) {
    var n = 0;
    r.subscribe(m(e, function(i) {
      ++n <= t && (e.next(i), t <= n && e.complete());
    }));
  });
}
function tt(t) {
  return t <= 0 ? function() {
    return ue;
  } : w(function(r, e) {
    var n = [];
    r.subscribe(m(e, function(i) {
      n.push(i), t < n.length && n.shift();
    }, function() {
      var i, o;
      try {
        for (var s = S(n), c = s.next(); !c.done; c = s.next()) {
          var u = c.value;
          e.next(u);
        }
      } catch (a) {
        i = { error: a };
      } finally {
        try {
          c && !c.done && (o = s.return) && o.call(s);
        } finally {
          if (i) throw i.error;
        }
      }
      e.complete();
    }, void 0, function() {
      n = null;
    }));
  });
}
function G(t, r) {
  return w(function(e, n) {
    var i = null, o = 0, s = !1, c = function() {
      return s && !i && n.complete();
    };
    e.subscribe(m(n, function(u) {
      i == null || i.unsubscribe();
      var a = 0, l = o++;
      O(t(u, l)).subscribe(i = m(n, function(d) {
        return n.next(r ? r(u, d, l, a++) : d);
      }, function() {
        i = null, c();
      }));
    }, function() {
      s = !0, c();
    }));
  });
}
function rt(t) {
  return w(function(r, e) {
    O(t).subscribe(m(e, function() {
      return e.complete();
    }, B)), !e.closed && r.subscribe(e);
  });
}
function U(t, r, e) {
  var n = h(t) || r || e ? { next: t, error: r, complete: e } : t;
  return n ? w(function(i, o) {
    var s;
    (s = n.subscribe) === null || s === void 0 || s.call(n);
    var c = !0;
    i.subscribe(m(o, function(u) {
      var a;
      (a = n.next) === null || a === void 0 || a.call(n, u), o.next(u);
    }, function() {
      var u;
      c = !1, (u = n.complete) === null || u === void 0 || u.call(n), o.complete();
    }, function(u) {
      var a;
      c = !1, (a = n.error) === null || a === void 0 || a.call(n, u), o.error(u);
    }, function() {
      var u, a;
      c && ((u = n.unsubscribe) === null || u === void 0 || u.call(n)), (a = n.finalize) === null || a === void 0 || a.call(n);
    }));
  }) : se;
}
function I(t, r = document) {
  if (r === null) return null;
  const e = String(t).split(">>>");
  let n = r;
  return e.find((i, o) => (o === 0 ? n = r.querySelector(e[o]) : n instanceof Element && (n = ((n == null ? void 0 : n.shadowRoot) ?? n).querySelector(e[o])), n === null)), n === r ? null : n;
}
function q(t) {
  return t > 1 ? t : window.innerWidth * t;
}
const nt = (t, r) => r.length && t.composedPath().some((e) => e instanceof Element && e.matches(r.join())), de = {
  haPanelEnergy: {
    onLock: () => {
      const t = I(
        "home-assistant >>> home-assistant-main >>> ha-drawer ha-panel-energy >>> ha-top-app-bar-fixed >>> header"
      );
      t && (t.style.top = "0px");
    }
  }
};
function ot() {
  Object.assign(document.body.style, {
    position: "fixed",
    inset: 0,
    top: `-${document.documentElement.scrollTop}px`
  }), Object.values(de).forEach(({ onLock: t }) => t == null ? void 0 : t());
}
function it() {
  const t = Math.abs(parseInt(document.body.style.top)) || document.documentElement.scrollTop;
  Object.assign(document.body.style, {
    position: "",
    inset: ""
  }), window.scrollTo({ top: t, left: 0, behavior: "auto" }), Object.values(de).forEach(({ onUnlock: r }) => r == null ? void 0 : r());
}
const st = ({
  startThreshold: t,
  endThreshold: r,
  preventOthers: e,
  lockVerticalScroll: n,
  exclusions: i
}) => g(document, "touchstart", {
  capture: e
}).pipe(
  P((o) => !nt(o, i)),
  P(({ touches: [{ clientX: o }] }) => o < q(t)),
  U((o) => {
    n && ot(), e && o.stopPropagation();
  }),
  G(
    ({ touches: [{ clientY: o }] }) => g(document, "touchmove", {
      capture: e
    }).pipe(
      P(({ touches: s }) => s.length < 2),
      U((s) => e && (s == null ? void 0 : s.stopPropagation())),
      rt(
        g(document, "touchend", {
          capture: e
        }).pipe(
          U((s) => {
            n && it(), e && (s == null || s.stopPropagation());
          }),
          he(1)
        )
      ),
      tt(1),
      T(({ changedTouches: [{ clientX: s, clientY: c }] }) => ({
        x: s,
        y: c
      })),
      P(({ x: s, y: c }) => s > Math.abs(c - o) && s > q(r))
    )
  )
), at = ({ preventOthers: t, threshold: r }) => g(document, "touchstart").pipe(
  U((e) => t && e.stopPropagation()),
  G(
    ({ touches: [{ clientX: e }] }) => g(document, "touchend").pipe(
      P(
        ({ changedTouches: [{ clientX: n }] }) => e - n > q(r)
      ),
      he(1)
    )
  )
);
let X = !1;
const ut = (t) => {
  var y, f;
  if (X)
    return !0;
  const r = I("home-assistant >>> home-assistant-main >>> ha-drawer"), e = I("ha-sidebar", r);
  if (!e || getComputedStyle(e).display === "none")
    return !1;
  if (!t) {
    const v = I("ha-panel-lovelace", r);
    t = ((f = (y = v == null ? void 0 : v.lovelace) == null ? void 0 : y.config) == null ? void 0 : f.sidebar_swipe) || {};
  }
  const {
    start_threshold: n = 0.1,
    end_threshold: i = 0.13,
    back_threshold: o = 50,
    prevent_others: s = !0,
    lock_vertical_scroll: c = !0,
    exclusions: u = []
  } = t, a = new Oe(!1), l = at({
    threshold: o,
    preventOthers: s
  }), d = st({
    startThreshold: n,
    endThreshold: i,
    preventOthers: s,
    lockVerticalScroll: c,
    exclusions: u
  });
  return r && new MutationObserver((v) => {
    a.next(v[0].oldValue === null);
  }).observe(r, {
    attributes: !0,
    attributeOldValue: !0,
    attributeFilter: ["open"]
  }), a.pipe(
    G(
      (v) => v ? l.pipe(T(() => !1)) : d.pipe(T(() => !0))
    )
  ).subscribe((v) => {
    var p;
    (p = I("home-assistant >>> home-assistant-main")) == null || p.dispatchEvent(
      new CustomEvent("hass-toggle-menu", { detail: { open: v } })
    );
  }), X = !0, !0;
};
var ct = "M2,21V19H20V21H2M20,8V5H18V8H20M20,3A2,2 0 0,1 22,5V8A2,2 0 0,1 20,10H18V13A4,4 0 0,1 14,17H8A4,4 0 0,1 4,13V3H20M16,5H6V13A2,2 0 0,0 8,15H14A2,2 0 0,0 16,13V5Z";
const lt = async (t, r) => {
  let e = null;
  try {
    e = await t.callWS({
      type: "supervisor/api",
      endpoint: `/addons/${r}/info`,
      method: "get"
    });
  } catch {
  }
  return e;
}, Z = async (t) => {
  const e = (await t.callWS({
    type: "supervisor/api",
    endpoint: "/ingress/session",
    method: "post"
  })).session;
  return document.cookie = `ingress_session=${e};path=/api/hassio_ingress/;SameSite=Strict${location.protocol === "https:" ? ";Secure" : ""}`, e;
}, ft = async (t, r) => {
  await t.callWS({
    type: "supervisor/api",
    endpoint: "/ingress/validate_session",
    method: "post",
    data: { session: r }
  });
}, ht = async (t, r, e, n) => {
  const i = (a) => {
    (t.shadowRoot || t).innerHTML = `<pre>${a}</pre>`;
  }, o = await lt(r, e);
  if (!o)
    return i(`Unable to fetch add-on info of '${e}'`);
  if (!o.ingress_url)
    return i(`Add-on '${e}' does not support Ingress`);
  const s = o.ingress_url.replace(/\/+$/, "");
  let c;
  const u = t;
  u._sessionKeepAlive && clearInterval(u._sessionKeepAlive);
  try {
    c = await Z(r);
  } catch {
    return i("Unable to create an Ingress session");
  }
  return u._sessionKeepAlive = window.setInterval(async () => {
    try {
      await ft(r, c);
    } catch {
      c = await Z(r);
    }
  }, 6e4), s;
};
class dt extends HTMLElement {
  constructor() {
    super(), this._panelPath = "", this.attachShadow({ mode: "open" });
  }
  async setProperties(r) {
    this._setProperties && this._setProperties(r);
    const e = this._getPanelConfig(r);
    if (!e)
      return;
    const n = await this._getTargetUrl(e, r);
    n && await this._createIngressView(n, e, r);
  }
  _getPanelConfig(r) {
    var s, c, u;
    if (!r.panel && r.route && (r.panel = (c = (s = r.hass) == null ? void 0 : s.panels) == null ? void 0 : c[r.route.prefix.slice(1)]), !r.panel)
      return;
    const e = r.panel;
    let { config: n, title: i, url_path: o } = e;
    if (n.children) {
      const a = (((u = r.route) == null ? void 0 : u.path) || "").split("/")[1];
      a && Object.hasOwn(n.children, a) && (n = n.children[a], o = `${o}/${a}`);
    } else
      n.title = i || "";
    if (this._panelPath !== o)
      return this._panelPath = o, n;
  }
  async _getTargetUrl(r, e) {
    let n = "";
    const i = new URLSearchParams(window.location.search), { url: o, addon: s } = r, c = o === void 0;
    if (typeof o == "object") {
      const { match: a, replace: l } = o;
      if (n = o.default, a) {
        const d = window.location.origin, y = d.replace(new RegExp(`^${a}$`, "i"), l);
        d !== y && (n = y);
      }
    } else if (c) {
      if (n = `/api/ingress/${r.token.value}`, s) {
        const a = await ht(this, e.hass, s);
        if (!a)
          return;
        n = a;
      }
    } else
      n = o;
    let { index: u } = r;
    if (u !== void 0) {
      const a = i.get("index");
      a && !/(^|\/)\.\.\//.test(a) && (u = a.replace(/^\/+/, "")), n = `${n}/${u}`;
    }
    if (r.token && !c) {
      const a = new URL(n);
      a.searchParams.set("ingressToken", r.token.value), n = a.href;
    }
    if (i.has("replace"))
      window.location.href = n;
    else if (r.ui_mode === "replace")
      n.indexOf("://") !== -1 && (window.location.href = n), pe(n, { replace: !0 });
    else
      return n;
  }
  async _createIngressView(r, e, n) {
    const { title: i } = e;
    let o = `
<iframe ${i ? `title="${i}"` : ""} src="${r}" allow="fullscreen"></iframe>
`, s = `
  iframe {
    border: 0;
    width: 100%;
    height: 100%;
    display: block;
    background-color: var(--primary-background-color);
  }
`;
    const c = e.ui_mode === "toolbar";
    /*!showToolbar &&*/
    ut() && (o += '<div id="swipebar"></div>', s += `
  #swipebar {
    position: fixed;
    top: 0;
    width: 20px;
    height: 100%;
  }
`), c && (await ve("iframe"), o = `<hass-subpage main-page>${o}
<ha-icon-button slot="toolbar-icon"></ha-icon-button>
</hass-subpage>`);
    const u = this.shadowRoot;
    if (u.innerHTML = `<style>${s}</style>${o}`, c) {
      const a = u.querySelector("hass-subpage");
      this._setButtons(a), a.header = i, this._setProperties = (l) => {
        for (const d of ["hass", "narrow"])
          d in l && (a[d] = l[d]);
      }, this._setProperties(n);
    }
  }
  _setButtons(r) {
    for (const [e, n] of r.querySelectorAll("ha-icon-button").entries())
      switch (e) {
        case 0: {
          n.label = "Donate", n.path = ct, n.addEventListener("click", () => {
            const i = document.createElement("a");
            i.href = "https://buymeacoffee.com/lovelylain", i.target = "_blank", i.rel = "noreferrer", i.click();
          });
          break;
        }
      }
  }
}
customElements.define("ha-panel-ingress", dt);
