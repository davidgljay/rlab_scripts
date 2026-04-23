const https = require('https');

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
      res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(raw) }));
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function main(args) {
  const apiKey = process.env.RESEND_API_KEY;
  const toEmail = process.env.TO_EMAIL;
  const fromEmail = process.env.FROM_EMAIL;

  if (!apiKey || !toEmail || !fromEmail) {
    return { statusCode: 500, body: { error: 'Missing required environment variables' } };
  }

  const subject = args.subject || 'New form submission';
  const form = args.form || {};
  const body = Object.entries(form)
    .map(([key, value]) => `<p><strong>${key}:</strong> ${value}</p>`)
    .join('\n');

  const { status, body: resBody } = await postJson(
    'https://api.resend.com/emails',
    { Authorization: `Bearer ${apiKey}` },
    { from: fromEmail, to: toEmail, subject, html: body }
  );

  if (status >= 400) {
    return { statusCode: status, body: { error: resBody } };
  }

  return { statusCode: 200, body: { id: resBody.id } };
}

module.exports = { main };
