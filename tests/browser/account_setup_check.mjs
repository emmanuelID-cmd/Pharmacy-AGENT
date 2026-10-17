// Synthetic account setup; no live recovery proof or external call.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
async function fixture({proof='a'.repeat(64),failure=false,pending=false,revoked=true}={}) {
  const nodes=new Map(),calls=[],history=[];
  class Element {
    constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this.dataset={};this.attributes={};this.value='';this.hidden=false;this.disabled=false;this.textContent='';this.classList={toggle(){}};}
    append(...values){values.forEach(value=>{value.parent=this;this.children.push(value);});}
    replaceChildren(...values){this.children=values;}
    setAttribute(name,value){this.attributes[name]=value;}
    addEventListener(name,fn){this.listeners[name]=fn;}
    focus(){this.focused=true;}
    all(){return this.children.flatMap(child=>[child,...child.all()]);}
    querySelector(selector){return this.all().find(node=>selector==='li'?node.tag==='li':node.href===selector.match(/href="([^"]+)"/)?.[1])||null;}
    closest(tag){return this.tag===tag?this:this.parent?.closest(tag);}
    remove(){this.parent.children=this.parent.children.filter(child=>child!==this);}
  }
  ['account-setup-form','setup-email','setup-password','setup-confirm','setup-errors','setup-submit','setup-status',
    'setup-email-error','setup-password-error','setup-confirm-error'].forEach(id=>nodes.set(id,new Element()));
  const get=id=>nodes.get(id);get('account-setup-form').dataset.configured='true';
  const ctx=vm.createContext({URLSearchParams,AbortController,clearTimeout,setTimeout:(fn,delay)=>setTimeout(fn,pending?5:delay),
    document:{getElementById:get,createElement:tag=>new Element(tag)},navigator:{onLine:true},
    async fetch(path,options){calls.push([path,JSON.parse(options.body)]);return {ok:!failure,json:async()=>pending?new Promise(()=>{}):failure?{message:'private-provider-secret'}:{state:'PASSWORD_SET',sessions_revoked:revoked}};}});
  ctx.window=ctx;ctx.location={hash:'#token_hash='+proof};ctx.history={replaceState:(...args)=>history.push(args)};
  vm.runInContext(fs.readFileSync('web/assets/account-setup.js','utf8'),ctx);
  const submit=()=>get('account-setup-form').listeners.submit({preventDefault(){}});
  const valid=()=>{get('setup-email').value='reviewer@example.test';get('setup-password').value='synthetic-long-password';get('setup-confirm').value='synthetic-long-password';};
  return {get,calls,history,submit,valid};
}
const missing=await fixture();assert.equal(missing.history[0][2],'/account/setup');await missing.submit();
assert.equal(missing.calls.length,0);assert.equal(missing.get('setup-errors').hidden,false);
missing.get('setup-email').value='reviewer@example.test';missing.get('setup-email').listeners.input();
assert.equal(missing.get('setup-email').attributes['aria-invalid'],'false');assert.equal(missing.get('setup-password').attributes['aria-invalid'],'true');
const mismatch=await fixture();mismatch.valid();mismatch.get('setup-confirm').value='different-password';await mismatch.submit();assert.equal(mismatch.calls.length,0);
const success=await fixture();success.valid();await success.submit();assert.equal(success.calls.length,1);
assert.equal(success.calls[0][1].token_hash,'a'.repeat(64));assert.equal(success.get('account-setup-form').hidden,true);
assert.equal(success.get('setup-password').value,'');assert.equal(success.get('setup-confirm').value,'');
const noProof=await fixture({proof:''});noProof.valid();await noProof.submit();assert.equal(noProof.calls.length,0);assert.match(noProof.get('setup-status').textContent,/fresh/);
for(const options of [{failure:true},{pending:true}]) {
  const failed=await fixture(options);failed.valid();await failed.submit();assert.match(failed.get('setup-status').textContent,/fresh/);
  assert.equal(failed.get('setup-status').textContent.includes('private-provider-secret'),false);
  assert.equal(failed.get('setup-submit').disabled,false);assert.equal(failed.get('setup-password').value,'');
  failed.valid();await failed.submit();assert.equal(failed.calls.length,1);assert.match(failed.get('setup-status').textContent,/finished/);
}
const cleanup=await fixture({revoked:false});cleanup.valid();await cleanup.submit();assert.match(cleanup.get('setup-status').textContent,/cleanup could not be confirmed/);
console.log('PASS: fragment cleanup, required fields, independent error correction, password match, no-proof denial, successful setup, redacted failure, timeout and no automatic replay. No sends.');
