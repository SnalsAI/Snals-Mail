const express = require('express');
const router = express.Router();
const emailController = require('../controllers/emailController');
const authMiddleware = require('../utils/authMiddleware');

// All routes require authentication
router.use(authMiddleware);

// Email routes
router.get('/', emailController.getAllEmails);
router.get('/:id', emailController.getEmail);
router.post('/:id/analyze', emailController.analyzeEmail);
router.patch('/:id', emailController.updateEmailStatus);
router.delete('/:id', emailController.deleteEmail);
router.post('/sync', emailController.syncEmails);

module.exports = router;
