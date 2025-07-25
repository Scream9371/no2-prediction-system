// Chart.js type definitions for IDE support
declare class Chart {
    constructor(ctx: CanvasRenderingContext2D, config: any);
    destroy(): void;
    update(): void;
    render(): void;
}

declare namespace Chart {
    interface ChartConfiguration {
        type: string;
        data: any;
        options?: any;
    }
}