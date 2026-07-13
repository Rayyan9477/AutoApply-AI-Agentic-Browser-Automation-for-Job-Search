import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAppStore } from '@/store/useAppStore';

describe('useAppStore', () => {
  beforeEach(() => {
    useAppStore.setState({ notification: null, wsConnected: false, pendingIntervention: null });
  });

  it('has correct initial state', () => {
    const state = useAppStore.getState();
    expect(state.notification).toBeNull();
    expect(state.wsConnected).toBe(false);
    expect(state.pendingIntervention).toBeNull();
  });

  // --- Notifications ---

  it('showNotification creates notification with default severity "info"', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid-1' });

    useAppStore.getState().showNotification('Test message');
    const notification = useAppStore.getState().notification;

    expect(notification).not.toBeNull();
    expect(notification?.message).toBe('Test message');
    expect(notification?.severity).toBe('info');
    expect(notification?.id).toBe('test-uuid-1');

    vi.unstubAllGlobals();
  });

  it('showNotification creates notification with explicit severity', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid-2' });

    useAppStore.getState().showNotification('Error occurred', 'error');
    const notification = useAppStore.getState().notification;

    expect(notification?.message).toBe('Error occurred');
    expect(notification?.severity).toBe('error');

    vi.unstubAllGlobals();
  });

  it('showNotification supports all severity levels', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid' });

    const severities = ['success', 'error', 'warning', 'info'] as const;
    for (const severity of severities) {
      useAppStore.getState().showNotification(`msg-${severity}`, severity);
      expect(useAppStore.getState().notification?.severity).toBe(severity);
    }

    vi.unstubAllGlobals();
  });

  it('showNotification replaces any existing notification', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'uuid-first' });
    useAppStore.getState().showNotification('First');

    vi.stubGlobal('crypto', { randomUUID: () => 'uuid-second' });
    useAppStore.getState().showNotification('Second', 'warning');

    const notification = useAppStore.getState().notification;
    expect(notification?.message).toBe('Second');
    expect(notification?.id).toBe('uuid-second');

    vi.unstubAllGlobals();
  });

  it('clearNotification sets notification to null', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid' });
    useAppStore.getState().showNotification('Will be cleared');
    useAppStore.getState().clearNotification();

    expect(useAppStore.getState().notification).toBeNull();

    vi.unstubAllGlobals();
  });

  it('clearNotification is safe to call when no notification exists', () => {
    useAppStore.getState().clearNotification();
    expect(useAppStore.getState().notification).toBeNull();
  });

  // --- WebSocket ---

  it('setWsConnected sets wsConnected to true', () => {
    useAppStore.getState().setWsConnected(true);
    expect(useAppStore.getState().wsConnected).toBe(true);
  });

  it('setWsConnected sets wsConnected to false', () => {
    useAppStore.setState({ wsConnected: true });
    useAppStore.getState().setWsConnected(false);
    expect(useAppStore.getState().wsConnected).toBe(false);
  });

  // --- Interventions ---

  it('setIntervention stores the pending intervention', () => {
    useAppStore.getState().setIntervention({ application_id: 'app-1', kind: 'captcha', prompt: 'Solve it' });
    expect(useAppStore.getState().pendingIntervention?.application_id).toBe('app-1');
  });

  it('clearIntervention resets the pending intervention to null', () => {
    useAppStore.getState().setIntervention({ application_id: 'app-1', kind: 'captcha', prompt: 'Solve it' });
    useAppStore.getState().clearIntervention();
    expect(useAppStore.getState().pendingIntervention).toBeNull();
  });

  // --- Cross-state independence ---

  it('notification changes do not affect other state', () => {
    useAppStore.setState({ wsConnected: true });
    vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid' });

    useAppStore.getState().showNotification('Hello');
    expect(useAppStore.getState().wsConnected).toBe(true);

    vi.unstubAllGlobals();
  });
});
