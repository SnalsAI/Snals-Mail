const Email = require('../models/Email');
const { simpleParser } = require('mailparser');
const Imap = require('imap');

// Get all emails
exports.getAllEmails = async (req, res) => {
  try {
    const {
      page = 1,
      limit = 20,
      status,
      folder,
      search
    } = req.query;

    const query = {};
    if (status) query.status = status;
    if (folder) query.folder = folder;
    if (search) {
      query.$text = { $search: search };
    }

    const emails = await Email.find(query)
      .sort({ date: -1 })
      .limit(limit * 1)
      .skip((page - 1) * limit)
      .exec();

    const count = await Email.countDocuments(query);

    res.json({
      emails,
      totalPages: Math.ceil(count / limit),
      currentPage: page,
      total: count
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

// Get single email
exports.getEmail = async (req, res) => {
  try {
    const email = await Email.findById(req.params.id);

    if (!email) {
      return res.status(404).json({ error: 'Email not found' });
    }

    // Mark as read
    if (email.status === 'unread') {
      email.status = 'read';
      await email.save();
    }

    res.json(email);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

// Analyze email
exports.analyzeEmail = async (req, res) => {
  try {
    const email = await Email.findById(req.params.id);

    if (!email) {
      return res.status(404).json({ error: 'Email not found' });
    }

    // Simple analysis (can be enhanced with ML/AI)
    const analysis = {
      spam_score: calculateSpamScore(email),
      sentiment: analyzeSentiment(email.body.text),
      category: categorizeEmail(email),
      keywords: extractKeywords(email.body.text || email.subject),
      priority: determinePriority(email)
    };

    email.analysis = analysis;
    await email.save();

    res.json({ email, analysis });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

// Update email status
exports.updateEmailStatus = async (req, res) => {
  try {
    const { status, folder } = req.body;
    const email = await Email.findById(req.params.id);

    if (!email) {
      return res.status(404).json({ error: 'Email not found' });
    }

    if (status) email.status = status;
    if (folder) email.folder = folder;

    await email.save();
    res.json(email);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

// Delete email
exports.deleteEmail = async (req, res) => {
  try {
    const email = await Email.findByIdAndDelete(req.params.id);

    if (!email) {
      return res.status(404).json({ error: 'Email not found' });
    }

    res.json({ message: 'Email deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

// Sync emails from IMAP server
exports.syncEmails = async (req, res) => {
  try {
    const { host, port, user, password, tls = true } = req.body;

    if (!host || !user || !password) {
      return res.status(400).json({ error: 'Missing IMAP configuration' });
    }

    const imap = new Imap({
      user,
      password,
      host,
      port: port || 993,
      tls,
      tlsOptions: { rejectUnauthorized: false }
    });

    let syncedCount = 0;

    imap.once('ready', () => {
      imap.openBox('INBOX', false, (err, box) => {
        if (err) throw err;

        const fetch = imap.seq.fetch('1:*', {
          bodies: '',
          struct: true
        });

        fetch.on('message', (msg) => {
          msg.on('body', async (stream) => {
            const parsed = await simpleParser(stream);

            try {
              await Email.findOneAndUpdate(
                { messageId: parsed.messageId },
                {
                  messageId: parsed.messageId,
                  from: {
                    address: parsed.from?.value[0]?.address,
                    name: parsed.from?.value[0]?.name
                  },
                  to: parsed.to?.value.map(t => ({
                    address: t.address,
                    name: t.name
                  })),
                  subject: parsed.subject,
                  body: {
                    text: parsed.text,
                    html: parsed.html
                  },
                  date: parsed.date,
                  attachments: parsed.attachments?.map(a => ({
                    filename: a.filename,
                    contentType: a.contentType,
                    size: a.size
                  })),
                  headers: parsed.headers
                },
                { upsert: true, new: true }
              );
              syncedCount++;
            } catch (error) {
              console.error('Error saving email:', error);
            }
          });
        });

        fetch.once('end', () => {
          imap.end();
        });
      });
    });

    imap.once('error', (err) => {
      res.status(500).json({ error: err.message });
    });

    imap.once('end', () => {
      res.json({
        message: 'Sync completed',
        syncedEmails: syncedCount
      });
    });

    imap.connect();
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

// Helper functions for email analysis
function calculateSpamScore(email) {
  let score = 0;
  const text = (email.body.text || '').toLowerCase();

  // Simple spam indicators
  const spamWords = ['viagra', 'lottery', 'winner', 'free money', 'click here', 'urgent'];
  spamWords.forEach(word => {
    if (text.includes(word)) score += 0.2;
  });

  return Math.min(score, 1);
}

function analyzeSentiment(text) {
  if (!text) return 'neutral';

  const positive = ['great', 'excellent', 'good', 'happy', 'thanks'];
  const negative = ['bad', 'terrible', 'angry', 'sad', 'problem'];

  let score = 0;
  const lowerText = text.toLowerCase();

  positive.forEach(word => {
    if (lowerText.includes(word)) score++;
  });

  negative.forEach(word => {
    if (lowerText.includes(word)) score--;
  });

  if (score > 0) return 'positive';
  if (score < 0) return 'negative';
  return 'neutral';
}

function categorizeEmail(email) {
  const subject = (email.subject || '').toLowerCase();
  const text = (email.body.text || '').toLowerCase();
  const combined = subject + ' ' + text;

  if (combined.includes('invoice') || combined.includes('payment')) return 'financial';
  if (combined.includes('meeting') || combined.includes('schedule')) return 'meeting';
  if (combined.includes('urgent') || combined.includes('important')) return 'urgent';
  if (combined.includes('newsletter') || combined.includes('subscribe')) return 'newsletter';

  return 'general';
}

function extractKeywords(text) {
  if (!text) return [];

  const words = text.toLowerCase()
    .replace(/[^\w\s]/g, '')
    .split(/\s+/)
    .filter(word => word.length > 4);

  const frequency = {};
  words.forEach(word => {
    frequency[word] = (frequency[word] || 0) + 1;
  });

  return Object.entries(frequency)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([word]) => word);
}

function determinePriority(email) {
  const subject = (email.subject || '').toLowerCase();

  if (subject.includes('urgent') || subject.includes('asap')) return 'urgent';
  if (subject.includes('important')) return 'high';

  return 'normal';
}
