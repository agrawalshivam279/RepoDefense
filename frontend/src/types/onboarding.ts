export type TourPlacement = "top" | "bottom" | "left" | "right" | "center";

export interface TourStep {
  id: string;
  targetSelector?: string;
  title: string;
  description: string;
  placement?: TourPlacement;
  badge?: string;
}

export interface TourConfig {
  tourId: string;
  steps: TourStep[];
  autoStart?: boolean;
  onComplete?: () => void;
  onSkip?: () => void;
}

export interface TourRect {
  top: number;
  left: number;
  width: number;
  height: number;
  bottom: number;
  right: number;
}
