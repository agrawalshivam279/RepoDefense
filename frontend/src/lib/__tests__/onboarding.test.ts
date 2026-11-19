import { beforeEach, describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  calculateCardPosition,
  DASHBOARD_TOUR_ID,
  DASHBOARD_TOUR_STEPS,
  getTourStorageKey,
  isTourCompleted,
  resetTourStatus,
  setTourCompleted,
} from "../onboarding";
import type { TourRect } from "@/types/onboarding";

describe("onboarding - Tour Configuration & Geometry Logic", () => {
  beforeEach(() => {
    const store: Record<string, string> = {};
    (globalThis as unknown as { localStorage: Storage }).localStorage = {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => {
        store[key] = value;
      },
      removeItem: (key: string) => {
        delete store[key];
      },
      clear: () => {
        for (const k of Object.keys(store)) delete store[k];
      },
      length: 0,
      key: () => null,
    };
  });

  it("verifies dashboard tour steps are well-formed", () => {
    assert.strictEqual(DASHBOARD_TOUR_ID, "dashboard_overview");
    assert.ok(DASHBOARD_TOUR_STEPS.length >= 4);

    for (const step of DASHBOARD_TOUR_STEPS) {
      assert.ok(step.id.length > 0, "step must have id");
      assert.ok(step.title.length > 0, "step must have title");
      assert.ok(step.description.length > 0, "step must have description");
    }
  });

  it("generates correct storage keys and manages tour completion state", () => {
    const key = getTourStorageKey("test_tour");
    assert.strictEqual(key, "repodefense_tour_test_tour_completed");

    assert.strictEqual(isTourCompleted("test_tour"), false);
    setTourCompleted("test_tour");
    assert.strictEqual(isTourCompleted("test_tour"), true);
    resetTourStatus("test_tour");
    assert.strictEqual(isTourCompleted("test_tour"), false);
  });

  it("calculates centered position when target is null or placement is center", () => {
    const posNull = calculateCardPosition(null, "bottom", 1200, 800);
    assert.strictEqual(posNull.isCentered, true);
    assert.strictEqual(posNull.left, 600);
    assert.strictEqual(posNull.top, 400);

    const mockRect: TourRect = {
      top: 100,
      left: 100,
      width: 200,
      height: 50,
      bottom: 150,
      right: 300,
    };

    const posCenter = calculateCardPosition(mockRect, "center", 1000, 600);
    assert.strictEqual(posCenter.isCentered, true);
    assert.strictEqual(posCenter.left, 500);
    assert.strictEqual(posCenter.top, 300);
  });

  it("calculates offset placement and clamps within viewport boundaries", () => {
    const mockRect: TourRect = {
      top: 100,
      left: 200,
      width: 150,
      height: 40,
      bottom: 140,
      right: 350,
    };

    // Bottom placement
    const posBottom = calculateCardPosition(mockRect, "bottom", 1000, 800);
    assert.strictEqual(posBottom.isCentered, false);
    assert.ok(posBottom.top > mockRect.bottom);
    assert.ok(posBottom.left >= 14);

    // Top placement
    const posTop = calculateCardPosition(mockRect, "top", 1000, 800);
    assert.strictEqual(posTop.isCentered, false);
    assert.ok(posTop.top >= 14);

    // Clamp right boundary
    const edgeRect: TourRect = {
      top: 100,
      left: 950,
      width: 40,
      height: 40,
      bottom: 140,
      right: 990,
    };
    const posRightClamp = calculateCardPosition(edgeRect, "bottom", 1000, 800);
    assert.ok(posRightClamp.left <= 1000 - 360 - 14);
  });
});
