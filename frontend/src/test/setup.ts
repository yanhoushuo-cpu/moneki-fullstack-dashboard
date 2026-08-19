import '@testing-library/jest-dom/vitest';

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = ResizeObserverStub as typeof ResizeObserver;

const getBoundingClientRect = HTMLElement.prototype.getBoundingClientRect;
HTMLElement.prototype.getBoundingClientRect = function getTestBoundingClientRect() {
  if (this.classList.contains('recharts-responsive-container')) {
    return {
      x: 0,
      y: 0,
      width: 800,
      height: 315,
      top: 0,
      right: 800,
      bottom: 315,
      left: 0,
      toJSON: () => ({}),
    };
  }
  return getBoundingClientRect.call(this);
};
