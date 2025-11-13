const mongoose = require('mongoose');

const emailSchema = new mongoose.Schema({
  messageId: {
    type: String,
    required: true,
    unique: true
  },
  from: {
    address: String,
    name: String
  },
  to: [{
    address: String,
    name: String
  }],
  subject: {
    type: String,
    required: true
  },
  body: {
    text: String,
    html: String
  },
  date: {
    type: Date,
    default: Date.now
  },
  attachments: [{
    filename: String,
    contentType: String,
    size: Number,
    path: String
  }],
  headers: mongoose.Schema.Types.Mixed,
  analysis: {
    spam_score: Number,
    sentiment: String,
    category: String,
    keywords: [String],
    priority: {
      type: String,
      enum: ['low', 'normal', 'high', 'urgent'],
      default: 'normal'
    }
  },
  status: {
    type: String,
    enum: ['unread', 'read', 'archived', 'deleted'],
    default: 'unread'
  },
  flags: [String],
  folder: {
    type: String,
    default: 'inbox'
  }
}, {
  timestamps: true
});

// Indexes for better performance
emailSchema.index({ subject: 'text', 'body.text': 'text' });
emailSchema.index({ date: -1 });
emailSchema.index({ 'from.address': 1 });
emailSchema.index({ status: 1 });

module.exports = mongoose.model('Email', emailSchema);
