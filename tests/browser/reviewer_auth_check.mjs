// Login/recovery simulations with synthetic credentials; no real Auth calls.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
async function fixture({configured=true,pending=false,rejected=false,destination='/demo'}={}) {
  const nodes=new Map(),calls=[],navigations=[];
  class Element {
    constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this.dataset={};this.attributes={};this.value='';this.hidden=false;this.disabled=false;this.textContent='';this.classes=new Set();this.classList={toggle:(name,on)=>on?this.classes.add(name):this.classes.delete(name)};}
    append(...values){values.forEach(value=>{value.parent=this;this.children.push(value);});}
    replaceChildren(...values){this.children=values;}
    setAttribute(name,value){this.attributes[name]=value;}
    addEventListener(name,fn){this.listeners[name]=fn;}
    focus(){this.focused=true;}
    querySelector(selector){const descendants=this.children.flatMap(child=>[child,...child.all()]);return descendants.find(node=>selector==='li'?node.tag==='li':node.href===selector.match(/href="([^"]+)"/)?.[1])||null;}
    all(){return this.children.flatMap(child=>[child,...child.all()]);}
    closest(tag){return this.tag===tag?this:this.parent?.closest(tag);}
    remove(){this.parent.children=this.parent.children.filter(child=>child!==this);}
  }
  ['reviewer-login-form','reviewer-sign-in','login-email','login-password','login-email-error','login-password-error','login-errors','login-status','reviewer-sign-out','reviewer-auth-status','reviewer-auth-required','reviewer-sign-in-link'].forEach(id=>{const e=new Element();e.id=id;nodes.set(id,e);});
  const get=id=>nodes.get(id)||null;
  get('reviewer-login-form').dataset={configured:String(configured),returnTo:'/demo'};
  get('reviewer-sign-in').disabled=!configured;
  get('reviewer-auth-required').hidden=true;
  const ctx=vm.createContext({URL,AbortController,encodeURIComponent,clearTimeout,setTimeout:(fn,delay)=>setTimeout(fn,pending?5:delay),document:{getElementById:get,createElement:tag=>new Element(tag)},navigator:{onLine:true},
    async fetch(path,options){calls.push([path,JSON.parse(options.body)]);return {ok:!rejected,json:async()=>pending?new Promise(()=>{}):rejected?{reason_code:'AUTH_LOGIN_REJECTED',message:'native-private-token'}:{state:'SIGNED_IN',redirect_to:destination}};}});
  ctx.window=ctx;ctx.location={origin:'https://demo.example',pathname:'/demo',search:'?order=demo-012345abcdef',replace:path=>navigations.push(path)};
  vm.runInContext(fs.readFileSync('web/assets/auth.js','utf8'),ctx);
  const submit=()=>get('reviewer-login-form').listeners.submit({preventDefault(){}});
  const valid=()=>{get('login-email').value='reviewer@example.test';get('login-password').value='synthetic-password';};
  return {get,calls,navigations,submit,valid,ctx};
}
const invalid=await fixture();await invalid.submit();
assert.equal(invalid.calls.length,0);assert.equal(invalid.get('login-errors').hidden,false);assert.equal(invalid.get('login-email').attributes['aria-invalid'],'true');
invalid.get('login-email').value='reviewer@example.test';invalid.get('login-email').listeners.input();
assert.equal(invalid.get('login-email').attributes['aria-invalid'],'false');assert.equal(invalid.get('login-password').attributes['aria-invalid'],'true');assert.equal(invalid.get('login-errors').hidden,false);
const rejected=await fixture({rejected:true});rejected.valid();await rejected.submit();
assert.match(rejected.get('login-status').textContent,/not accepted/);assert.equal(rejected.get('login-status').textContent.includes('native-private'),false);
assert.equal(rejected.get('login-email').value,'reviewer@example.test');assert.equal(rejected.get('login-password').value,'');assert.equal(rejected.get('reviewer-sign-in').disabled,false);
const success=await fixture();success.valid();await success.submit();
assert.deepEqual(success.navigations,['https://demo.example/demo']);assert.equal(success.calls[0][0],'/api/auth/login');assert.equal(success.get('login-password').value,'');
const pending=await fixture({pending:true});pending.valid();await pending.submit();
assert.match(pending.get('login-status').textContent,/not confirmed/);assert.equal(pending.calls.length,1);assert.equal(pending.get('reviewer-sign-in').disabled,false);
const wrongDestination=await fixture({destination:'https://untrusted.example'});wrongDestination.valid();await wrongDestination.submit();assert.equal(wrongDestination.navigations.length,0);
const disabled=await fixture({configured:false});disabled.valid();await disabled.submit();assert.equal(disabled.calls.length,0);
const logout=await fixture();await logout.get('reviewer-sign-out').listeners.click();assert.deepEqual(logout.navigations,['/login']);assert.equal(logout.calls[0][0],'/api/auth/logout');
const expired=await fixture();expired.ctx.handleAuthRequired({status:401,headers:{get:()=> 'required'}});assert.equal(expired.get('reviewer-auth-required').hidden,false);assert.match(expired.get('reviewer-sign-in-link').href,/^\/login\?next=/);
console.log('PASS: required-field feedback, generic denial, password clearing/email preservation, bounded timeout recovery, same-origin redirect, logout and expired-session guidance. Synthetic credentials only.');
