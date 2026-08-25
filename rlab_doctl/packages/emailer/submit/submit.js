const https = require('https');
const crypto = require('crypto');

function postJson(url, headers, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const options = {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) },
    };
    const req = https.request(url, options, (res) => {
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

function base64url(input) {
  return Buffer.from(input)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

async function getGoogleAccessToken(serviceAccountEmail, privateKey, scope) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: 'RS256', typ: 'JWT' };
  const claims = {
    iss: serviceAccountEmail,
    scope,
    aud: 'https://oauth2.googleapis.com/token',
    iat: now,
    exp: now + 3600,
  };

  const unsigned = `${base64url(JSON.stringify(header))}.${base64url(JSON.stringify(claims))}`;
  const signer = crypto.createSign('RSA-SHA256');
  signer.update(unsigned);
  signer.end();
  const signature = signer.sign(privateKey.replace(/\\n/g, '\n'))
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');

  const assertion = `${unsigned}.${signature}`;

  const { status, body } = await postJson(
    'https://oauth2.googleapis.com/token',
    {},
    { grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion }
  );

  if (status >= 400 || !body.access_token) {
    throw new Error(`Failed to get Google access token: ${JSON.stringify(body)}`);
  }

  return body.access_token;
}

async function appendSheetRow(form) {
  const serviceAccountEmail = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
  const privateKey = process.env.GOOGLE_PRIVATE_KEY;
  const sheetId = process.env.GOOGLE_SHEET_ID;
  const range = process.env.GOOGLE_SHEET_RANGE || 'Sheet1!A:A';

  if (!serviceAccountEmail || !privateKey || !sheetId) {
    throw new Error('Missing required Google Sheets environment variables');
  }

  const accessToken = await getGoogleAccessToken(
    serviceAccountEmail,
    privateKey,
    'https://www.googleapis.com/auth/spreadsheets'
  );

  const row = [
    new Date().toISOString(),
    form.name || '',
    form.email || '',
    form.organization || '',
    Array.isArray(form.role) ? form.role.join(', ') : (form.role || ''),
    Array.isArray(form.interest) ? form.interest.join(', ') : (form.interest || ''),
    form.why || '',
  ];

  const url = `https://sheets.googleapis.com/v4/spreadsheets/${sheetId}/values/${encodeURIComponent(range)}:append?valueInputOption=USER_ENTERED`;
  const { status, body } = await postJson(
    url,
    { Authorization: `Bearer ${accessToken}` },
    { values: [row] }
  );

  if (status >= 400) {
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
