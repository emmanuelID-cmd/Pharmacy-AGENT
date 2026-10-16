// Browser integration checks against the local application using an isolated CDP browser.
// Start Chrome headless with --remote-debugging-port=8768 and a new temporary profile.
import fs from 'node:fs';
const origin = process.argv[2] || 'http://127.0.0.1:8770';
if (!['127.0.0.1', 'localhost'].includes(new URL(origin).hostname)) throw Error('Loopback test target required');
const targets = await (await fetch('http://127.0.0.1:8768/json/list')).json();
const target = targets.find(t => t.type === 'page');
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
let sequence = 0;
const pending = new Map(), exceptions = [];
socket.addEventListener('message', event => {
  const response = JSON.parse(event.data);
  if (response.method === 'Runtime.exceptionThrown') exceptions.push(response.params.exceptionDetails.text);
  const entry = pending.get(response.id);
  if (entry) { pending.delete(response.id); response.error ? entry.reject(Error(JSON.stringify(response.error))) : entry.resolve(response.result); }
});
function call(method, params = {}) { return new Promise((resolve, reject) => { const id = ++sequence; pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })); }); }
async function evaluate(expression) {
  const r = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
}
async function navigate(path) {
  await call('Page.navigate', { url: origin + path });
  for (let i = 0; i < 60; i++) {
    const ready = await evaluate('document.readyState === "complete" && !!document.getElementById("main-content")');
    if (ready) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw Error('Page did not load ' + path);
}
await call('Page.enable'); await call('Runtime.enable');
await call('Emulation.setDeviceMetricsOverride', { width: 1024, height: 1000, deviceScaleFactor: 1, mobile: false });
const routes = ['/', '/agent', '/tools', '/harness', '/injection-risk-test', '/failure-state', '/demo', '/architecture'];
const layouts = [];
for (const width of [1024, 640, 320]) {
  await call('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
  let baseline;
  for (const path of routes) {
    await navigate(path);
    const check = await evaluate(`(()=>{const nav=document.querySelector('.primary-nav');const header=document.querySelector('.site-header');return {path:location.pathname,overflow:document.documentElement.scrollWidth>innerWidth,navY:nav.getBoundingClientRect().y,headerY:header.getBoundingClientRect().y,labels:Array.from(nav.querySelectorAll('a')).map(a=>a.textContent),active:nav.querySelector('[aria-current="page"]')?.getAttribute('href'),back:!!document.querySelector('[data-back]')};})()`);
    if (check.overflow || check.active !== path || check.back) throw Error('Route/layout failed ' + JSON.stringify(check));
    if (path === '/') {
      const catalog = await evaluate(`(()=>{const table=document.querySelector('.catalog-table');const scroll=document.querySelector('.catalog-scroll');return {rows:table?.tBodies[0].rows.length,columns:table?.tHead.rows[0].cells.length,first:table?.tBodies[0].rows[0].cells[0].textContent,last:table?.tBodies[0].rows[149].cells[0].textContent,scrollable:scroll.scrollWidth>scroll.clientWidth,focusable:scroll.tabIndex===0};})()`);
      if (catalog.rows !== 150 || catalog.columns !== 32 || catalog.first !== 'catalog-001' || catalog.last !== 'catalog-150' || !catalog.scrollable || !catalog.focusable) throw Error('Catalog layout failed ' + JSON.stringify(catalog));
    }
    if (check.labels.join('|') !== 'Home|Agent|Tools|Harness|Injection Risk Test|Failure State|Demo|Architecture') throw Error('Navigation order');
    baseline ??= check;
    if (check.navY !== baseline.navY || check.headerY !== baseline.headerY) throw Error('Shared shell shifted');
  }
  layouts.push({ width, routes: 8, overflow: false, sharedShellAligned: true });
}
await call('Emulation.setDeviceMetricsOverride', { width: 1024, height: 1000, deviceScaleFactor: 1, mobile: false });
await navigate('/agent');
const inputChecks = await evaluate(`(async()=>{
 const results=[];const byId=id=>document.getElementById(id);function check(name,ok){if(!ok)throw Error(name);results.push(name);}
 function fill(text){byId('review-request').value=text;byId('review-request').dispatchEvent(new Event('input',{bubbles:true}));}
 function submit(){byId('review-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}
 const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 fill('');submit();check('Blank error summary',!byId('review-errors').hidden&&byId('review-request').getAttribute('aria-invalid')==='true');
 fill('   ');submit();check('Whitespace rejected',!byId('review-errors').hidden);
 fill('x'.repeat(1001));submit();check('Oversize preserved',!byId('review-errors').hidden&&byId('review-request').value.length===1001);
 fill('x'.repeat(1002));check('Invalid edit retains feedback',!byId('request-error').hidden);
 fill('💊'.repeat(1000));check('Unicode codepoint boundary',byId('request-counter').textContent==='1,000 / 1,000'&&byId('request-error').hidden);
 fill('Review inventory — café فريق');document.querySelector('a[data-route="/tools"]').click();for(let i=0;i<40&&location.pathname!='/tools';i++)await pause(50);check('Real URL navigation',location.pathname==='/tools');
 document.querySelector('a[data-route="/agent"]').click();for(let i=0;i<40&&location.pathname!='/agent';i++)await pause(50);check('Draft preserved across routes',byId('review-request').value==='Review inventory — café فريق');
 const links=Array.from(document.querySelectorAll('.primary-nav a'));links[1].focus();links[1].dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));check('Keyboard arrows',document.activeElement===links[2]);
 return results;
})()`);
await navigate('/demo');
const demoChecks = await evaluate(`(async()=>{
 document.getElementById('run-demo').click();for(let i=0;i<80&&document.getElementById('demo-result').hidden;i++)await new Promise(resolve=>setTimeout(resolve,50));
 const result=document.getElementById('demo-result');const rows=result.querySelectorAll('tbody tr:not(.report-detail-row)');
 if(rows.length!==20||result.textContent.includes('ActionUnavailable'))throw Error('Demo rows/actions');
 if(!result.textContent.includes('MAINTAIN')||!result.textContent.includes('MANUAL_REVIEW')||!result.textContent.includes('SYNTHETIC-v0'))throw Error('Demo evidence');
 if(!result.querySelector('details'))throw Error('Evidence expansion');
 return {rows:rows.length,actionsShown:true,evidenceShown:true,modelCalled:false};
})()`);
await navigate('/injection-risk-test');
const testerChecks = await evaluate(`(async()=>{
 const byId=id=>document.getElementById(id);const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 for(let i=0;i<80&&byId('test-sample').options.length<2;i++)await pause(50);
 byId('test-sample').value='request';byId('tester-form').requestSubmit();for(let i=0;i<80&&byId('tester-result').hidden;i++)await pause(50);
 if(!byId('tester-result').textContent.includes('DENIED')||!byId('tester-result').textContent.includes('Operational write effects0'))throw Error('Forbidden write tester');
 byId('test-sample').value='normal';byId('output-change').value='alter_days';byId('tester-form').requestSubmit();for(let i=0;i<80&&!byId('tester-result').textContent.includes('Rejected changed report');i++)await pause(50);
 if(!byId('tester-result').textContent.includes('Rejected changed report'))throw Error('Tamper guard');
 return {forbiddenWriteDenied:true,changedOutputRejected:true};
})()`);
await navigate('/failure-state');
const failureChecks = await evaluate(`(async()=>{
 document.getElementById('failure-scenario').value='offline';document.getElementById('preview-failure').click();for(let i=0;i<80&&!document.getElementById('failure-result').textContent.includes('Simulated scenario');i++)await new Promise(resolve=>setTimeout(resolve,50));
 const result=document.getElementById('failure-result');if(result.classList.contains('is-loading')||!result.textContent.includes('simulated'))throw Error('Failure state');return {simulatedOfflineLabel:true,loadingCleared:true};
})()`);
await call('Emulation.setDeviceMetricsOverride', { width: 320, height: 1000, deviceScaleFactor: 1, mobile: false });
await navigate('/demo');
await evaluate(`(async()=>{document.getElementById('run-demo').click();for(let i=0;i<80&&document.getElementById('demo-result').hidden;i++)await new Promise(r=>setTimeout(r,50));if(document.documentElement.scrollWidth>innerWidth)throw Error('Mobile report overflow');})()`);
await call('Emulation.setEmulatedMedia', { features: [{name:'prefers-color-scheme',value:'dark'}] });
await evaluate(`(()=>{const s=getComputedStyle(document.body);if(s.backgroundColor==='rgb(243, 246, 242)')throw Error('Dark appearance did not apply');})()`);
await call('Emulation.setEmulatedMedia', { features: [{name:'prefers-color-scheme',value:'light'}] });
await call('Emulation.setDeviceMetricsOverride', { width: 1024, height: 900, deviceScaleFactor: 1, mobile: false });
await navigate('/');
const screenshot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
const output = process.env.TEMP + '/pharmacy-working-home.png';
fs.writeFileSync(output, Buffer.from(screenshot.data, 'base64'));
if(exceptions.length)throw Error('Browser exceptions: '+JSON.stringify(exceptions));
console.log(JSON.stringify({layouts,inputChecks,demoChecks,testerChecks,failureChecks,browserExceptions:exceptions,screenshot:output},null,2));
await navigate('/demo');
const closingChecks = await evaluate(`(async()=>{
 const get=id=>document.getElementById(id), pause=()=>new Promise(r=>setTimeout(r,50));
 get('close-day').click();for(let i=0;i<100&&get('closing-workspace').hidden;i++)await pause();
 if(get('closing-workspace').hidden)throw Error('Closing workspace missing');
 const original=get('closing-report').textContent;
 if(get('order-item').options.length!==151)throw Error('150-item dropdown missing');
 get('order-add-form').requestSubmit();if(get('order-add-errors').hidden)throw Error('Catalog selection validation missing');
 get('demo-order-form').requestSubmit();if(get('order-errors').hidden)throw Error('Empty order validation missing');
 const close=await (await fetch('/api/closing-demo/close',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
 const valid=close.closing.rows.find(row=>row.suggestion.suggested_quantity>0);
 const add=()=>{get('order-search').value=valid.item_id;get('order-search').dispatchEvent(new Event('input'));get('order-item').value=valid.item_id;get('order-item').dispatchEvent(new Event('change'));get('order-add-form').requestSubmit();};
 add();if(get('order-list').children.length!==1)throw Error('Order row not added');
 const input=()=>get('qty-'+valid.item_id);
 input().value='3';input().dispatchEvent(new Event('input'));add();
 if(get('order-list').children.length!==1||input().value!=='3')throw Error('Duplicate selection discarded human edit');
 input().value='0';input().dispatchEvent(new Event('input'));get('demo-order-form').requestSubmit();
 if(get('order-errors').hidden||input().getAttribute('aria-invalid')!=='true')throw Error('Quantity error missing');
 input().value='4';input().dispatchEvent(new Event('input'));if(input().getAttribute('aria-invalid')!=='false')throw Error('Quantity error did not clear');
 const second=close.closing.rows.find(row=>row.item_id!==valid.item_id&&row.suggestion.suggested_quantity>0);
 get('order-search').value=second.item_id;get('order-search').dispatchEvent(new Event('input'));get('order-item').value=second.item_id;get('order-add-form').requestSubmit();
 for(const rowInput of get('order-list').querySelectorAll('input')){rowInput.value='0';rowInput.dispatchEvent(new Event('input'));}
 get('demo-order-form').requestSubmit();
 if(get('order-errors').querySelectorAll('li').length!==2)throw Error('Both quantity errors not summarized');
 get('qty-'+second.item_id).closest('article').querySelector('button').click();
 if(get('order-errors').hidden||get('order-errors').querySelectorAll('li').length!==1||input().getAttribute('aria-invalid')!=='true')throw Error('Removing one row hid unrelated errors');
 get('clear-demo-order').click();if(get('order-list').children.length!==0)throw Error('Reject did not clear');
 add();input().value='3';input().dispatchEvent(new Event('input'));
 return {itemId:valid.item_id,original,closingId:close.closing.closing_id,catalogEntries:150,selectionValidation:true,quantityValidation:true,rejection:true};
})()`);
await evaluate(`document.querySelector('a[data-route="/tools"]').click()`);
for(let i=0;i<50&&await evaluate('location.pathname!=="/tools"');i++)await new Promise(r=>setTimeout(r,50));
await evaluate(`document.querySelector('a[data-route="/demo"]').click()`);
for(let i=0;i<50&&await evaluate('location.pathname!=="/demo"');i++)await new Promise(r=>setTimeout(r,50));
const closingResult = await evaluate(`(async()=>{
 const get=id=>document.getElementById(id),pause=()=>new Promise(r=>setTimeout(r,50));
 if(get('order-list').children.length!==1||get('qty-'+${JSON.stringify(closingChecks.itemId)}).value!=='3')throw Error('Closing draft did not survive tab return');
 get('demo-order-form').requestSubmit();for(let i=0;i<100&&get('order-result').hidden;i++)await pause();
 if(get('order-result').hidden||!get('order-result').textContent.includes('SIMULATED_SUBMISSION'))throw Error('Human submit missing');
 const original=${JSON.stringify(closingChecks.original)};
 if(get('closing-report').textContent!==original)throw Error('Submission rewrote inventory report');
 get('close-day').click();for(let i=0;i<100&&get('close-day').disabled;i++)await pause();
 if(get('closing-report').textContent!==original)throw Error('Repeated close created second report');
 const state=await(await fetch('/api/closing-demo/close',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
 if(state.closing.closing_id!==${JSON.stringify(closingChecks.closingId)}||state.order.order_placed||state.order.test_sms.external_sends!==0||state.order.manufacturer_notice.external_sends!==0)throw Error('Closing effects violated');
 return {sameReport:true,tabDraftPreserved:true,humanSubmittedSimulation:true,externalSends:0,inventoryWrites:state.order.inventory_write_effects};
})()`);
await call('Emulation.setDeviceMetricsOverride', {width:320,height:1000,deviceScaleFactor:1,mobile:false});
if(await evaluate('document.documentElement.scrollWidth>innerWidth'))throw Error('Closing mobile overflow');
await call('Emulation.setDeviceMetricsOverride', {width:1200,height:1000,deviceScaleFactor:1,mobile:false});
await evaluate(`document.getElementById('closing-title').scrollIntoView()`);
const closingShot = await call('Page.captureScreenshot', {format:'png'});
const closingOutput = process.env.TEMP + '/pharmacy-closing-demo.png';
fs.writeFileSync(closingOutput, Buffer.from(closingShot.data,'base64'));
if(exceptions.length)throw Error('Browser exceptions: '+JSON.stringify(exceptions));
console.log(JSON.stringify({closingChecks:{...closingChecks,original:undefined},closingResult,closingScreenshot:closingOutput},null,2));
await navigate('/demo');
await evaluate(`(async()=>{
 const get=id=>document.getElementById(id);get('close-day').click();
 for(let i=0;i<100&&get('order-result').hidden;i++)await new Promise(r=>setTimeout(r,50));
 const restored=get('qty-'+${JSON.stringify(closingChecks.itemId)});
 if(!restored||restored.value!=='3'||!restored.disabled||!get('order-empty').hidden)throw Error('Submitted order reload recovery failed');
})()`);
console.log(JSON.stringify({submittedOrderRecoveredAfterReload:true}));
const repeatOrders = await evaluate(`(async()=>{
 const get=id=>document.getElementById(id), pause=()=>new Promise(r=>setTimeout(r,50));
 const before=await(await fetch('/api/closing-demo/close',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
 if(get('new-demo-order').hidden||get('new-demo-order').disabled)throw Error('New order unavailable after reload');
 get('new-demo-order').click();
 if(get('order-search').disabled||get('submit-demo-order').disabled||get('order-list').children.length)throw Error('New order did not unlock empty form');
 get('order-search').value=${JSON.stringify(closingChecks.itemId)};get('order-search').dispatchEvent(new Event('input'));
 get('order-item').value=${JSON.stringify(closingChecks.itemId)};get('order-add-form').requestSubmit();
 const quantity=get('qty-'+${JSON.stringify(closingChecks.itemId)});quantity.value='4';quantity.dispatchEvent(new Event('input'));
 get('close-day').click();for(let i=0;i<100&&get('close-day').disabled;i++)await pause();
 if(get('qty-'+${JSON.stringify(closingChecks.itemId)}).value!=='4'||get('submit-demo-order').disabled)throw Error('View same report overwrote new draft');
 get('demo-order-form').requestSubmit();for(let i=0;i<100&&(get('order-result').hidden||get('new-demo-order').disabled);i++)await pause();
 const after=await(await fetch('/api/closing-demo/close',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
 if(after.orders.length!==2||before.order.order_id===after.order.order_id)throw Error('Second distinct order missing');
 if(JSON.stringify(before.closing)!==JSON.stringify(after.closing))throw Error('Second order changed closing report');
 if(after.orders[0].lines[0].quantity!==3||after.orders[1].lines[0].quantity!==4)throw Error('Order history changed or lost');
 if(!get('order-history').textContent.includes('2 submitted demo order'))throw Error('History count missing');
 if(get('new-demo-order').disabled)throw Error('Next draft unavailable after submit');
 return {secondOrderAfterReload:true,originalReportUnchanged:true,historyPreserved:true};
})()`);
console.log(JSON.stringify({repeatOrders}));
await call('Browser.close');socket.close();
