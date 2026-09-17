// Record the installed DSH session API; the pinned headless CLI has no --json.
import { appendFileSync } from 'node:fs';

export const name = 'mip-session-recorder';
export const inject = ['sessions'];

export function apply(ctx) {
  const path = process.env.MIP_DSH_EVENTS;
  if (!path) throw new Error('MIP_DSH_EVENTS is required');
  const keep = new Set([
    'system/message', 'user/message', 'assistant/message', 'tool/call',
    'tool/result', 'turn/start', 'turn/end', 'step/start', 'request/header',
  ]);
  ctx.on('session/event', (session, event) => {
    if (!keep.has(event.type)) return;
    appendFileSync(path, JSON.stringify({ session_id: session.id, ...event }) + '\n');
  });
}
