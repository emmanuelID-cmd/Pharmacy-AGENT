/* Individual sign-in; provider/database tokens never reach this page. */
(() => {
  'use strict';
  const get = id => document.getElementById(id);
  const emailValid = value => value.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  const messages = {
    AUTH_LOGIN_REJECTED: 'Sign-in was not accepted. Check your email/password and that your account setup and team access are complete.',
    AUTH_NOT_CONFIGURED: 'Individual login is not configured on this server. Ask the project owner to complete the server settings.',
    AUTH_SERVICE_UNAVAILABLE: 'Temporarily Unavailable. Sign-in or sign-out could not be confirmed. Retry when the service is available.',
    AUTH_RATE_LIMITED: 'Too many sign-in attempts. Wait a minute before trying again.',
    INVALID_FORM_INPUT: 'Check the email address and enter your account password.',
    ORIGIN_REQUIRED: 'Reload this page directly, then try signing in again.',
    ORIGIN_NOT_ALLOWED: 'Open this site directly, then try again.'
  };
  function status(id, message, error = false, loading = false) {
    const target = get(id); if (!target) return;
    target.hidden = false; target.textContent = message;
    target.classList.toggle('is-error', error); target.classList.toggle('is-loading', loading);
  }
  async function request(path, body) {
    const controller = new AbortController(); let timer;
    try {
      return await Promise.race([(async () => {
        const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body), signal:controller.signal});
        const result = await response.json();
        if (!response.ok) {const error=Error(); error.code=Object.hasOwn(messages,result.reason_code)?result.reason_code:'AUTH_SERVICE_UNAVAILABLE'; throw error;}
        return result;
      })(),new Promise((_,reject) => {timer=setTimeout(() => {controller.abort();reject(Error());},20000);})]);
    } finally {clearTimeout(timer);controller.abort();}
  }
  function safeMessage(error) {
    return navigator.onLine === false ? 'No Internet Access. Reconnect, then try again. Your email is preserved.' : messages[error?.code] || 'The request was not confirmed. Retry sign-in or sign-out; no automatic retry will run.';
  }
  window.handleAuthRequired = response => {
    if (response.status !== 401 || response.headers?.get?.('X-Pharmacy-Authentication') !== 'required') return false;
    const banner=get('reviewer-auth-required'), link=get('reviewer-sign-in-link');
    if (banner) banner.hidden=false;
    if (link) link.href='/login?next='+encodeURIComponent(window.location.pathname+window.location.search);
    return true;
  };
  window.bindReviewerAuth = () => {
    const form=get('reviewer-login-form'), signOut=get('reviewer-sign-out');
    if (form && !form.dataset.bound) {
      form.dataset.bound='true'; let busy=false;
      const clearField = (id, valid) => {
        const input=get(id); if (!valid) return;
        input.setAttribute('aria-invalid','false');get(id+'-error').hidden=true;
        const summary=get('login-errors');summary.querySelector('a[href="#'+id+'"]')?.closest('li').remove();
        summary.hidden=!summary.querySelector('li');
      };
      get('login-email').addEventListener('input',()=>clearField('login-email',emailValid(get('login-email').value.trim())));
      get('login-password').addEventListener('input',()=>clearField('login-password',get('login-password').value.length>0 && get('login-password').value.length<=1024));
      form.addEventListener('submit', async event => {
        event.preventDefault(); if (busy || form.dataset.configured !== 'true') return;
        const email=get('login-email'),password=get('login-password'),invalid=[];
        const emailValue=email.value.trim();
        if (!emailValid(emailValue)) invalid.push(['login-email','Enter the email address for your approved account.']);
        if (!password.value || password.value.length>1024) invalid.push(['login-password','Enter your account password.']);
        const summary=get('login-errors'); summary.replaceChildren(); summary.hidden=!invalid.length;
        [email,password].forEach(input => {input.setAttribute('aria-invalid',String(invalid.some(([id])=>id===input.id)));get(input.id+'-error').hidden=!invalid.some(([id])=>id===input.id);});
        if (invalid.length) {
          const heading=document.createElement('strong');heading.textContent='Check your sign-in details';summary.append(heading);
          const list=document.createElement('ul');
          invalid.forEach(([id,message])=>{const item=document.createElement('li'),link=document.createElement('a');link.href='#'+id;link.textContent=message;link.addEventListener('click',e=>{e.preventDefault();get(id).focus();});item.append(link);list.append(item);});
          summary.append(list);summary.focus();return;
        }
        busy=true;get('reviewer-sign-in').disabled=true;form.setAttribute('aria-busy','true');
        status('login-status','Signing in…',false,true);
        try {
          const result=await request('/api/auth/login',{email:emailValue,password:password.value,return_to:form.dataset.returnTo||'/demo'});
          const destination=new URL(result.redirect_to,window.location.origin);
          if (destination.origin!==window.location.origin || !['/','/agent','/tools','/harness','/injection-risk-test','/failure-state','/demo','/architecture'].includes(destination.pathname)) throw Error();
          status('login-status','Signed in. Opening your workspace…');window.location.replace(destination.href);
        } catch(error) {status('login-status',safeMessage(error),true);}
        finally {password.value='';busy=false;get('reviewer-sign-in').disabled=false;form.setAttribute('aria-busy','false');}
      });
    }
    if (signOut && !signOut.dataset.bound) {
      signOut.dataset.bound='true';let busy=false;
      signOut.addEventListener('click',async()=>{
        if (busy)return;busy=true;signOut.disabled=true;status('reviewer-auth-status','Signing out…',false,true);
        try {await request('/api/auth/logout',{});window.location.replace('/login');}
        catch(error){status('reviewer-auth-status',safeMessage(error),true);}
        finally{busy=false;signOut.disabled=false;}
      });
    }
  };
  window.bindReviewerAuth();
})();
