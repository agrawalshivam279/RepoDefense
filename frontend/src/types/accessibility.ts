export type PolitenessSetting = "polite" | "assertive";

export interface Announcement {
  id: string;
  message: string;
  politeness: PolitenessSetting;
  timestamp: number;
}

export interface A11yShortcut {
  key: string;
  description: string;
  action: () => void;
}
