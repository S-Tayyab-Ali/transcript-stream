const { io } = require('socket.io-client');

const TRANSCRIPT_ID = process.argv[2] || 'mock_abc123';

const socket = io('http://localhost:8000', {
  path: '/ws/realtime',
  auth: {
    token: 'Bearer test-token-123',
    transcriptId: TRANSCRIPT_ID
  }
});

socket.on('auth.success', (data) => {
  console.log('Authenticated:', data);
});

socket.on('auth.failed', (err) => {
  console.log('Auth failed:', err);
  process.exit(1);
});

socket.on('connection.established', () => {
  console.log('Connection established, waiting for transcript...\n');
});

socket.on('transcription.broadcast', (event) => {
  const mins = Math.floor(event.start_time / 60);
  const secs = Math.floor(event.start_time % 60);
  const ts = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  console.log(`[${ts}] ${event.speaker_name}: ${event.text.substring(0, 80)}...`);
});

socket.on('disconnect', () => {
  console.log('\nDisconnected');
});
