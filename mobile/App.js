/**
 * Speech & Text Analyzer — Android App
 * TM471 Final Year Project | Ali Yasser Ali Mohammed | 21510864
 *
 * Connects to the Flask API (api.py) running on your PC over WiFi.
 *
 *   1. Start the server on your PC:   make api
 *   2. Start Expo (LAN):              make mobile
 *   3. Scan the QR code with Expo Go (same Wi‑Fi as the PC)
 *   4. API URL auto-detects in dev; use Settings (gear) to override
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import Constants from 'expo-constants';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, KeyboardAvoidingView, Platform, Alert,
  StatusBar, ActivityIndicator, Modal, Keyboard,
} from 'react-native';
import { Audio } from 'expo-av';
import axios from 'axios';

// ─── API URL (dev: same IP as Metro bundler) ───────────────────────────────

function devApiBase() {
  const debuggerHost =
    Constants.expoGoConfig?.debuggerHost ??
    Constants.manifest2?.extra?.expoGo?.debuggerHost ??
    Constants.manifest?.debuggerHost;
  if (!debuggerHost) return null;
  const host = debuggerHost.split(':')[0];
  return `http://${host}:5000`;
}

const DEFAULT_API_BASE = devApiBase() ?? 'http://127.0.0.1:5000';

// Colour palette — matches the desktop dark theme
const T = {
  bg:      '#0D1117',
  panel:   '#161B22',
  border:  '#30363D',
  accent:  '#58A6FF',   // blue  — user messages
  green:   '#3FB950',   // green — assistant messages
  yellow:  '#E3B341',   // amber — mic / warnings
  purple:  '#A78BFA',   // purple — NLP metadata
  white:   '#E6EDF3',
  muted:   '#8B949E',
  red:     '#F87171',
  codeBg:  '#1C2128',
};


// ─── Utility ────────────────────────────────────────────────────────────────

function fmt(arr, fallback = '—') {
  if (!arr || arr.length === 0) return fallback;
  if (typeof arr[0] === 'object') return arr.map(e => `${e.text}(${e.label})`).join(', ');
  return arr.join(', ');
}


// ─── Main component ─────────────────────────────────────────────────────────

export default function App() {
  const [messages,  setMessages]  = useState([
    { role: 'assistant', text: 'Hello! Type a message or hold Mic to speak.' },
  ]);
  const [input,     setInput]     = useState('');
  const [meta,      setMeta]      = useState({ intent: '—', keywords: '—', entities: '—' });
  const [status,    setStatus]    = useState('Connecting…');
  const [statusCol, setStatusCol] = useState(T.yellow);
  const [busy,      setBusy]      = useState(false);
  const [recording, setRecording] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [apiBase,   setApiBase]   = useState(DEFAULT_API_BASE);
  const [apiInput,  setApiInput]  = useState(DEFAULT_API_BASE);

  const scrollRef = useRef(null);

  // ── startup health check ──────────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        await axios.get(`${apiBase}/health`, { timeout: 5000 });
        setStatus('Ready');
        setStatusCol(T.muted);
      } catch {
        setStatus('Cannot reach server — check IP and WiFi');
        setStatusCol(T.red);
      }
    })();
  }, [apiBase]);

  // ── auto-scroll ───────────────────────────────────────────────────────────
  useEffect(() => {
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
  }, [messages]);

  // ── helpers ───────────────────────────────────────────────────────────────

  const addMessage = useCallback((role, text) => {
    setMessages(prev => [...prev, { role, text }]);
  }, []);

  const applyResult = useCallback((data) => {
    addMessage('assistant', data.reply);
    setMeta({
      intent:   data.intent   || '—',
      keywords: fmt(data.keywords),
      entities: fmt(data.entities),
    });
    setStatus('Ready');
    setStatusCol(T.muted);
    setBusy(false);
  }, [addMessage]);

  const handleError = useCallback((err) => {
    const msg = err?.response?.data?.error || err.message || 'Network error';
    addMessage('system', `Error: ${msg}`);
    setStatus('Error — try again');
    setStatusCol(T.red);
    setBusy(false);
  }, [addMessage]);

  // ── send text ─────────────────────────────────────────────────────────────

  const sendText = async () => {
    const text = input.trim();
    if (!text || busy) return;
    Keyboard.dismiss();
    setInput('');
    addMessage('user', text);
    setBusy(true);
    setStatus('Analysing…');
    setStatusCol(T.yellow);

    try {
      const { data } = await axios.post(
        `${apiBase}/chat`,
        { text },
        { timeout: 60000 },
      );
      applyResult(data);
    } catch (err) {
      handleError(err);
    }
  };

  // ── voice recording ───────────────────────────────────────────────────────

  const startRecording = async () => {
    if (busy || isRecording) return;

    try {
      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) {
        Alert.alert('Permission needed', 'Microphone access is required for voice input.');
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const rec = new Audio.Recording();
      await rec.prepareToRecordAsync({
        android: {
          extension: '.wav',
          outputFormat: Audio.AndroidOutputFormat.DEFAULT,
          audioEncoder: Audio.AndroidAudioEncoder.DEFAULT,
          sampleRate: 16000,
          numberOfChannels: 1,
          bitRate: 128000,
        },
        ios: {
          extension: '.m4a',
          outputFormat: Audio.IOSOutputFormat.MPEG4AAC,
          audioQuality: Audio.IOSAudioQuality.HIGH,
          sampleRate: 44100,
          numberOfChannels: 1,
          bitRate: 128000,
        },
      });

      await rec.startAsync();
      setRecording(rec);
      setIsRecording(true);
      setStatus('Listening — release to send');
      setStatusCol(T.yellow);
    } catch (err) {
      Alert.alert('Recording error', err.message);
    }
  };

  const stopRecording = async () => {
    if (!recording || !isRecording) return;

    setIsRecording(false);
    setStatus('Transcribing…');
    setStatusCol(T.yellow);
    setBusy(true);

    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);

      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });

      // Upload the audio file to the Flask /voice endpoint
      const formData = new FormData();
      const ext = uri.split('.').pop() || 'wav';
      formData.append('audio', {
        uri,
        name:  `recording.${ext}`,
        type:  ext === 'm4a' ? 'audio/m4a' : 'audio/wav',
      });

      const { data } = await axios.post(
        `${apiBase}/voice`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 90000,
        },
      );

      if (data.user_input) {
        addMessage('user', `🎙 ${data.user_input}`);
      }
      applyResult(data);
    } catch (err) {
      setRecording(null);
      handleError(err);
    }
  };

  // ── new chat ──────────────────────────────────────────────────────────────

  const newChat = async () => {
    if (busy) return;
    try {
      await axios.post(`${apiBase}/reset`, {}, { timeout: 5000 });
    } catch { /* ignore — history cleared on server regardless */ }
    setMessages([{ role: 'assistant', text: 'New chat started. Previous context cleared.' }]);
    setMeta({ intent: '—', keywords: '—', entities: '—' });
    setStatus('Ready');
    setStatusCol(T.muted);
  };

  // ── settings modal ────────────────────────────────────────────────────────

  const saveSettings = () => {
    setApiBase(apiInput.trim().replace(/\/$/, ''));
    setSettingsVisible(false);
    setStatus('Reconnecting…');
    setStatusCol(T.yellow);
  };

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={T.bg} />

      {/* ── Header ── */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Speech & Text Analyzer</Text>
          <Text style={styles.headerSub}>TM471 · Ali Yasser Ali · 21510864</Text>
        </View>
        <TouchableOpacity onPress={() => setSettingsVisible(true)} style={styles.settingsBtn}>
          <Text style={styles.settingsBtnText}>⚙</Text>
        </TouchableOpacity>
      </View>

      {/* ── Chat ── */}
      <ScrollView
        ref={scrollRef}
        style={styles.chat}
        contentContainerStyle={styles.chatContent}
        keyboardShouldPersistTaps="handled"
      >
        {messages.map((msg, i) => (
          <View key={i} style={styles.messageBlock}>
            <Text style={[
              styles.messageLabel,
              msg.role === 'user'   ? { color: T.accent } :
              msg.role === 'system' ? { color: T.red }    :
                                     { color: T.green },
            ]}>
              {msg.role === 'user'      ? 'You' :
               msg.role === 'assistant' ? 'Assistant' : 'System'}
            </Text>
            <Text style={styles.messageText}>{msg.text}</Text>
            <View style={styles.divider} />
          </View>
        ))}

        {busy && (
          <View style={styles.loadingRow}>
            <ActivityIndicator size="small" color={T.accent} />
            <Text style={styles.loadingText}>{status}</Text>
          </View>
        )}
      </ScrollView>

      {/* ── NLP Metadata strip ── */}
      <View style={styles.metaStrip}>
        <Text style={styles.metaText} numberOfLines={1}>
          Intent: <Text style={styles.metaVal}>{meta.intent}</Text>
          {'   '}Keywords: <Text style={styles.metaVal}>{meta.keywords}</Text>
          {'   '}Entities: <Text style={styles.metaVal}>{meta.entities}</Text>
        </Text>
      </View>

      {/* ── Input row ── */}
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.inputRow}>
          <TextInput
            style={styles.textInput}
            value={input}
            onChangeText={setInput}
            placeholder="Type a message…"
            placeholderTextColor={T.muted}
            onSubmitEditing={sendText}
            returnKeyType="send"
            editable={!busy}
            multiline={false}
          />

          <TouchableOpacity
            style={[styles.btn, styles.sendBtn, busy && styles.btnDisabled]}
            onPress={sendText}
            disabled={busy}
          >
            <Text style={styles.btnText}>Send</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.btn, styles.micBtn,
              isRecording && styles.micBtnRecording,
              busy && !isRecording && styles.btnDisabled,
            ]}
            onPressIn={startRecording}
            onPressOut={stopRecording}
            disabled={busy && !isRecording}
          >
            <Text style={styles.btnText}>{isRecording ? '⏹' : '🎙'}</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.btn, styles.newBtn, busy && styles.btnDisabled]}
            onPress={newChat}
            disabled={busy}
          >
            <Text style={[styles.btnText, { color: T.muted }]}>New</Text>
          </TouchableOpacity>
        </View>

        {/* ── Status bar ── */}
        <View style={styles.statusBar}>
          <Text style={[styles.statusText, { color: statusCol }]}>{status}</Text>
        </View>
      </KeyboardAvoidingView>

      {/* ── Settings Modal ── */}
      <Modal
        visible={settingsVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setSettingsVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>Server Settings</Text>
            <Text style={styles.modalLabel}>PC IP Address</Text>
            <Text style={styles.modalHint}>
              Run  python api.py  on your PC and enter the URL it prints.
            </Text>
            <TextInput
              style={styles.modalInput}
              value={apiInput}
              onChangeText={setApiInput}
              placeholder="http://192.168.1.x:5000"
              placeholderTextColor={T.muted}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.btn, styles.sendBtn]}
                onPress={saveSettings}
              >
                <Text style={styles.btnText}>Save</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.btn, styles.newBtn]}
                onPress={() => setSettingsVisible(false)}
              >
                <Text style={[styles.btnText, { color: T.muted }]}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}


// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: T.bg,
  },

  // Header
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: T.panel,
    paddingTop: 48,
    paddingBottom: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: T.border,
  },
  headerTitle: {
    color: T.accent,
    fontSize: 17,
    fontWeight: 'bold',
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier New',
  },
  headerSub: {
    color: T.muted,
    fontSize: 10,
    marginTop: 2,
  },
  settingsBtn: {
    padding: 8,
  },
  settingsBtnText: {
    color: T.muted,
    fontSize: 20,
  },

  // Chat
  chat: {
    flex: 1,
    backgroundColor: T.panel,
  },
  chatContent: {
    padding: 14,
    paddingBottom: 6,
  },
  messageBlock: {
    marginBottom: 4,
  },
  messageLabel: {
    fontSize: 11,
    fontWeight: 'bold',
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier New',
    marginBottom: 4,
    marginTop: 8,
  },
  messageText: {
    color: T.white,
    fontSize: 14,
    lineHeight: 21,
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier New',
  },
  divider: {
    height: 1,
    backgroundColor: T.border,
    marginTop: 10,
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 10,
  },
  loadingText: {
    color: T.muted,
    fontSize: 12,
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier New',
  },

  // NLP strip
  metaStrip: {
    backgroundColor: T.panel,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderTopWidth: 1,
    borderTopColor: T.border,
  },
  metaText: {
    color: T.muted,
    fontSize: 10,
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier New',
  },
  metaVal: {
    color: T.purple,
  },

  // Input row
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: T.bg,
    paddingHorizontal: 10,
    paddingVertical: 8,
    gap: 6,
    borderTopWidth: 1,
    borderTopColor: T.border,
  },
  textInput: {
    flex: 1,
    backgroundColor: T.panel,
    color: T.white,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier New',
    borderWidth: 1,
    borderColor: T.border,
  },
  btn: {
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtn: {
    backgroundColor: T.accent,
  },
  micBtn: {
    backgroundColor: T.panel,
    borderWidth: 1,
    borderColor: T.yellow,
  },
  micBtnRecording: {
    backgroundColor: T.red,
    borderColor: T.red,
  },
  newBtn: {
    backgroundColor: T.panel,
    borderWidth: 1,
    borderColor: T.border,
  },
  btnDisabled: {
    opacity: 0.4,
  },
  btnText: {
    color: T.white,
    fontWeight: 'bold',
    fontSize: 13,
  },

  // Status bar
  statusBar: {
    backgroundColor: T.bg,
    paddingHorizontal: 14,
    paddingBottom: Platform.OS === 'android' ? 10 : 24,
    paddingTop: 2,
  },
  statusText: {
    fontSize: 10,
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier New',
  },

  // Settings modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  modalBox: {
    backgroundColor: T.panel,
    borderRadius: 12,
    padding: 24,
    width: '100%',
    borderWidth: 1,
    borderColor: T.border,
  },
  modalTitle: {
    color: T.white,
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  modalLabel: {
    color: T.accent,
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  modalHint: {
    color: T.muted,
    fontSize: 11,
    marginBottom: 10,
    lineHeight: 16,
  },
  modalInput: {
    backgroundColor: T.codeBg,
    color: T.white,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier New',
    borderWidth: 1,
    borderColor: T.border,
    marginBottom: 16,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 10,
  },
});
