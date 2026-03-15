import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAppStore } from '@/store/useAppStore';

describe('useAppStore', () => {
  beforeEach(() => {
    // Reset to initial state before each test.
    useAppStore.setState({
      sidebarOpen: false,
      notification: null,
      wsConnected: false,
    });
  });

  it('has correct initial state', () => {
    const state = useAppStore.getState();
    expect(state.sidebarOpen).toBe(false);
    expect(state.notification).toBeNull();
    expect(state.wsConnected).toBe(false);
  });

  // --- Sidebar ---

  it('toggleSidebar flips sidebarOpen from false to true', () => {
    useAppStore.getState().toggleSidebar();
    expect(useAppStore.getState().sidebarOpen).toBe(true);
  });

  it('toggleSidebar flips sidebarOpen from true to false', () => {
    useAppStore.setState({ sidebarOpen: true });
    useAppStore.getState().toggleSidebar();
    expect(useAppStore.getState().sidebarOpen).toBe(false);
  });

  it('double toggle returns to original state', () => {
    useAppStore.getState().toggleSidebar();
    useAppStore.getState().toggleSidebar();
    expect(useAppStore.getState().sidebarOpen).toBe(false);
  });

  it('setSidebarOpen sets sidebar to true', () => {
    useAppStore.getState().setSidebarOpen(true);
    expect(useAppStore.getState().sidebarOpen).toBe(true);
  });

  it('setSidebarOpen sets sidebar to false', () => {
    useAppStore.setState({ sidebarOpen: true });
    useAppStore.getState().setSidebarOpen(false);
    expect(useAppStore.getState().sidebarOpen).toBe(false);
  });

  // --- Notifications ---

  it('showNotification creates notification with default severity "info"', () => {
    // Stub crypto.randomUUID for predictable id.
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

  // --- Cross-state independence ---

  it('notification changes do not affect other state', () => {
    useAppStore.setState({ sidebarOpen: true, wsConnected: true });
    vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid' });

    useAppStore.getState().showNotification('Hello');
    expect(useAppStore.getState().sidebarOpen).toBe(true);
    expect(useAppStore.getState().wsConnected).toBe(true);

    vi.unstubAllGlobals();
  });

  it('sidebar changes do not affect other state', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid' });
    useAppStore.getState().showNotification('Existing');
    useAppStore.getState().setWsConnected(true);

    useAppStore.getState().toggleSidebar();
    expect(useAppStore.getState().notification?.message).toBe('Existing');
    expect(useAppStore.getState().wsConnected).toBe(true);

    vi.unstubAllGlobals();
  });
});
