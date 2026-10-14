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
await call('Browser.close');socket.close();
