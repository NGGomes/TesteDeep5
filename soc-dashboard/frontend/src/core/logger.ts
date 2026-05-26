// core/logger.ts

export enum LogLevel {
 NONE = 0,
 ERROR = 1,
 WARN = 2,
 INFO = 3,      // Essencial (console)
 DEBUG = 4,     // Detalhado (storage)
 TRACE = 5,     // Muito detalhado (storage)
}

export interface LogEntry {
 timestamp: string;
 level: string;
 module: string;
 message: string;
 data?: any;
}

// Mapeamento de nível para valor numérico
const levelToValue: Record<string, LogLevel> = {
 'ERROR': LogLevel.ERROR,
 'WARN': LogLevel.WARN,
 'INFO': LogLevel.INFO,
 'DEBUG': LogLevel.DEBUG,
 'TRACE': LogLevel.TRACE,
};

function getLevelValue(level: string): LogLevel {
 return levelToValue[level] ?? LogLevel.INFO;
}

class Logger {
 private consoleLevel: LogLevel = LogLevel.INFO;
 private storageLevel: LogLevel = LogLevel.DEBUG;
 private maxStorageEntries: number = 10000;
 private storageKey: string = 'dashboard_debug_logs';
 private logs: LogEntry[] = [];

 constructor() {
  this.loadFromStorage();
  this.setupKeyboardShortcut();
 }

 private setupKeyboardShortcut(): void {
  // Ctrl+Shift+L para download de logs
  window.addEventListener('keydown', (e) => {
   if (e.ctrlKey && e.shiftKey && e.key === 'L') {
    e.preventDefault();
    this.downloadLogs();
    console.log('[Logger] Logs downloaded via keyboard shortcut');
   }
   // Ctrl+Shift+C para limpar logs
   if (e.ctrlKey && e.shiftKey && e.key === 'C') {
    e.preventDefault();
    this.clearLogs();
    console.log('[Logger] Logs cleared via keyboard shortcut');
   }
  });
 }

 private loadFromStorage(): void {
  try {
   const stored = localStorage.getItem(this.storageKey);
   if (stored) {
    this.logs = JSON.parse(stored);
    // Keep only last N entries
    if (this.logs.length > this.maxStorageEntries) {
     this.logs = this.logs.slice(-this.maxStorageEntries);
    }
    console.log(`[Logger] Loaded ${this.logs.length} logs from storage`);
   }
  } catch (e) {
   console.warn('[Logger] Failed to load logs from storage');
  }
 }

 private saveToStorage(): void {
  try {
   // Keep only last N entries
   if (this.logs.length > this.maxStorageEntries) {
    this.logs = this.logs.slice(-this.maxStorageEntries);
   }
   localStorage.setItem(this.storageKey, JSON.stringify(this.logs));
  } catch (e) {
   console.warn('[Logger] Failed to save logs to storage');
  }
 }

 private shouldLogToConsole(level: LogLevel): boolean {
  return level <= this.consoleLevel && level >= LogLevel.INFO;
 }

 private shouldLogToStorage(level: LogLevel): boolean {
  return level <= this.storageLevel;
 }

 private sanitizeData(data: any): any {
  if (!data) return data;
  try {
   // Remove circular references and large objects
   const seen = new WeakSet();
   return JSON.parse(JSON.stringify(data, (_, value) => {
    if (typeof value === 'object' && value !== null) {
     if (seen.has(value)) return '[Circular]';
     seen.add(value);
    }
    // Truncate long strings
    if (typeof value === 'string' && value.length > 500) {
     return value.substring(0, 500) + '...';
    }
    // Truncate large arrays
    if (Array.isArray(value) && value.length > 100) {
     return value.slice(0, 100).map(v => {
      if (typeof v === 'object' && v !== null) {
       return { ...v, _truncated: true };
      }
      return v;
     }).concat({ _truncated: true, _original_length: value.length });
    }
    return value;
   }));
  } catch (e) {
   return '[Unserializable]';
  }
 }

 private log(level: LogLevel, levelName: string, module: string, message: string, data?: any): void {
  const entry: LogEntry = {
   timestamp: new Date().toISOString(),
   level: levelName,
   module,
   message,
   data: data ? this.sanitizeData(data) : undefined,
  };

  // Console output (only INFO, WARN, ERROR)
  if (this.shouldLogToConsole(level)) {
   const consoleMsg = `[${module}] ${message}`;
   if (level === LogLevel.ERROR) {
    console.error(consoleMsg, data || '');
   } else if (level === LogLevel.WARN) {
    console.warn(consoleMsg, data || '');
   } else {
    console.log(consoleMsg, data ? '(see storage for details)' : '');
   }
  }

  // Storage output (all levels >= storageLevel)
  if (this.shouldLogToStorage(level)) {
   this.logs.push(entry);
   if (this.logs.length > this.maxStorageEntries) {
    this.logs = this.logs.slice(-this.maxStorageEntries);
   }
   this.saveToStorage();
  }
 }

 error(module: string, message: string, data?: any): void {
  this.log(LogLevel.ERROR, 'ERROR', module, message, data);
 }

 warn(module: string, message: string, data?: any): void {
  this.log(LogLevel.WARN, 'WARN', module, message, data);
 }

 info(module: string, message: string, data?: any): void {
  this.log(LogLevel.INFO, 'INFO', module, message, data);
 }

 debug(module: string, message: string, data?: any): void {
  this.log(LogLevel.DEBUG, 'DEBUG', module, message, data);
 }

 trace(module: string, message: string, data?: any): void {
  this.log(LogLevel.TRACE, 'TRACE', module, message, data);
 }

 getLogs(minLevel: LogLevel = LogLevel.DEBUG): LogEntry[] {
  return this.logs.filter(l => {
   const lvlValue = getLevelValue(l.level);
   return lvlValue <= minLevel;
  });
 }

 getLogsByModule(module: string, minLevel: LogLevel = LogLevel.DEBUG): LogEntry[] {
  return this.getLogs(minLevel).filter(l => l.module === module);
 }

 getLogsByLevel(level: LogLevel): LogEntry[] {
  const levelName = LogLevel[level];
  return this.logs.filter(l => l.level === levelName);
 }

 clearLogs(): void {
  this.logs = [];
  localStorage.removeItem(this.storageKey);
  this.info('Logger', 'Logs cleared');
 }

 downloadLogs(): void {
  const blob = new Blob([JSON.stringify(this.logs, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `dashboard_logs_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
  a.click();
  URL.revokeObjectURL(url);
  this.info('Logger', `Logs downloaded (${this.logs.length} entries)`);
 }

 setConsoleLevel(level: LogLevel): void {
  this.consoleLevel = level;
  const levelName = LogLevel[level];
  this.info('Logger', `Console level set to ${levelName}`);
 }

 setStorageLevel(level: LogLevel): void {
  this.storageLevel = level;
  const levelName = LogLevel[level];
  this.info('Logger', `Storage level set to ${levelName}`);
 }

 getStats(): { total: number; byLevel: Record<string, number>; byModule: Record<string, number> } {
  const byLevel: Record<string, number> = { ERROR: 0, WARN: 0, INFO: 0, DEBUG: 0, TRACE: 0 };
  const byModule: Record<string, number> = {};
  
  for (const log of this.logs) {
   byLevel[log.level] = (byLevel[log.level] || 0) + 1;
   byModule[log.module] = (byModule[log.module] || 0) + 1;
  }
  
  return {
   total: this.logs.length,
   byLevel,
   byModule,
  };
 }
}

export const logger = new Logger();

// Helper to log SSE events
export function logSSEEvent(module: string, eventType: string, payload: any): void {
 // Extract only relevant fields for storage (reduces noise)
 let simplifiedPayload: any = null;
 if (payload) {
  simplifiedPayload = {
   type: eventType,
   ...(payload.window_id && { window_id: payload.window_id }),
   ...(payload.alert_count && { alert_count: payload.alert_count }),
   ...(payload.reason && { reason: payload.reason }),
  };
  if (eventType === 'next_alert_info') {
   simplifiedPayload.current_index = payload.current_alert_index;
   simplifiedPayload.next_index = payload.next_alert_index;
   simplifiedPayload.gap_ms = payload.gap_ms;
   simplifiedPayload.is_last = payload.is_last;
  }
  if (eventType === 'dataset_bounds') {
   simplifiedPayload.total_alerts = payload.total_alerts;
   simplifiedPayload.speed_factor = payload.speed_factor;
   simplifiedPayload.first_alert = payload.first_alert?.number;
  }
 }
 logger.debug(module, `SSE:${eventType}`, simplifiedPayload);
}

// Helper to log window operations
export function logWindowOp(module: string, operation: string, windowId: string, data?: any): void {
 logger.debug(module, `Window ${operation}`, { windowId, ...data });
}

// Helper to log hypothesis confirmations (console essential)
export function logHypothesisConfirmed(module: string, label: string, score: number, riskTier?: string): void {
 const percent = (score * 100).toFixed(1);
 const tierInfo = riskTier ? ` [${riskTier}]` : '';
 logger.info(module, `✓ CONFIRMED: ${label} (${percent}%)${tierInfo}`);
}

// Helper to log errors (console always)
export function logError(module: string, message: string, error?: any): void {
 logger.error(module, message, error);
}

// Helper to log performance metrics
export function logPerf(module: string, operation: string, durationMs: number): void {
 logger.debug(module, `PERF:${operation}`, { durationMs });
}

