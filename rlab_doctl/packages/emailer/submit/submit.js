const https = require('https');

function get(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      let raw = '';
      res.on('data', (chunk) => { raw += chunk; });
      res.on('end', () => {
        let parsed;
        try { parsed = JSON.parse(raw); } catch (e) { parsed = raw; }
        resolve({ status: res.statusCode, body: parsed, headers: res.headers });
      });
    }).on('error', reject);
  });
}

function postJson(url, headers, body, redirectsLeft) {
  if (redirectsLeft === undefined) redirectsLeft = 5;

  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const options = {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) },
    };
    const req = https.request(url, options, (res) => {
      // Google Apps Script's /exec endpoint responds to POST with a 302 to
      // script.googleusercontent.com carrying the real body; follow it via GET.
      if ([301, 302, 303, 307].includes(res.statusCode) && res.headers.location && redirectsLeft > 0) {
        res.resume();
        resolve(get(res.headers.location));
        return;
      }

      let raw = '';
      res.on('data', (chunk) => { raw += chunk; });
      res.on('end', () => {
        let parsed;
        try { parsed = JSON.parse(raw); } catch (e) { parsed = raw; }
        resolve({ status: res.statusCode, body: parsed });
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function appendSheetRow(form) {
  const scriptUrl = process.env.APPS_SCRIPT_URL;
  const secret = process.env.APPS_SCRIPT_SECRET;

  if (!scriptUrl || !secret) {
    throw new Error('Missing required Apps Script environment variables');
  }

  const row = [
    new Date().toISOString(),
    form.name || '',
    form.email || '',
    form.organization || '',
    Array.isArray(form.role) ? form.role.join(', ') : (form.role || ''),
    Array.isArray(form.interest) ? form.interest.join(', ') : (form.interest || ''),
    form.why || '',
  ];

  const { status, body } = await postJson(scriptUrl, {}, { secret, row });

  if (status >= 400 || (body && body.ok === false)) {
    throw new Error(`Failed to append sheet row: ${JSON.stringify(body)}`);
  }

  return body;
}

async function sendEmail(subject, form) {
  const apiKey = process.env.RESEND_API_KEY;
  const toEmail = process.env.TO_EMAIL;
  const fromEmail = process.env.FROM_EMAIL;

  if (!apiKey || !toEmail || !fromEmail) {
    throw new Error('Missing required email environment variables');
  }

  const html = Object.entries(form)
    .map(([key, value]) => `<p><strong>${key}:</strong> ${Array.isArray(value) ? value.join(', ') : value}</p>`)
    .join('\n');

  const payload = { from: fromEmail, to: toEmail, subject, html };
  if (form.email) {
    payload.reply_to = form.email;
  }

  const { status, body } = await postJson(
    'https://api.resend.com/emails',
    { Authorization: `Bearer ${apiKey}` },
    payload
  );

  if (status >= 400) {
    throw new Error(`Failed to send email: ${JSON.stringify(body)}`);
  }

  return body;
}

async function main(args) {
  const subject = args.subject || 'New form submission';
  const form = args.form || {};

  const errors = {};
  let sheetResult = null;
  let emailResult = null;

  try {
    sheetResult = await appendSheetRow(form);
  } catch (e) {
    errors.sheet = e.message;
  }

  try {
    emailResult = await sendEmail(subject, form);
  } catch (e) {
    errors.email = e.message;
  }

  if (!sheetResult && !emailResult) {
    return { statusCode: 500, body: { error: 'Both sheet append and email send failed', errors } };
  }

  return {
    statusCode: 200,
    body: {
      sheet: sheetResult ? 'ok' : 'failed',
      email: emailResult ? 'ok' : 'failed',
      errors: Object.keys(errors).length ? errors : undefined,
    },
  };
}

module.exports = { main };
