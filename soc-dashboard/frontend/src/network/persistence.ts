import { STORAGE_KEYS } from '../core/constants';
import type { AlertPayload, SliceState, Agent2Report, TriggerMeta } from '../core/types';
import {
setAlerts, setSelectedHyp, setTotalReceived,
setAgent2Reports, setTriggerMeta, setSlice
} from '../core/store';

export function persist(key: string, value: unknown): void {
try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { }
}

export function restore<T>(key: string, fallback: T): T {
try {
 const raw = sessionStorage.getItem(key);
 if (raw === null) return fallback;
 return JSON.parse(raw) as T;
} catch { return fallback; }
}

export function loadPersistedState(): void {
const alerts = restore<AlertPayload[]>(STORAGE_KEYS.ALERTS, []);
setAlerts(alerts);

const selectedHyp = restore<number>(STORAGE_KEYS.SELECTED_HYP, 0);
setSelectedHyp(selectedHyp);

const totalReceived = restore<number>(STORAGE_KEYS.TOTAL_RECEIVED, 0);
setTotalReceived(totalReceived);

const agent2Reports = restore<Agent2Report[]>(STORAGE_KEYS.AGENT2_REPORTS, []);
setAgent2Reports(agent2Reports);

const triggerMeta = restore<Record<string, TriggerMeta>>(STORAGE_KEYS.TRIGGER_META, {});
setTriggerMeta(new Map(Object.entries(triggerMeta)));

const savedSlice = restore<SliceState | null>(STORAGE_KEYS.SLICE, null);
if (savedSlice) setSlice(savedSlice);
}

