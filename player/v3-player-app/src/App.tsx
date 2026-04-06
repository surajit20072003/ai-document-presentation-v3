import { V3Player } from './v3/V3Player';

interface AppProps {
    jobId: string;
}

export default function App({ jobId }: AppProps) {
    if (!jobId) {
        return (
            <div className="flex items-center justify-center h-full flex-col gap-4 text-white">
                <div className="text-5xl">🎓</div>
                <h1 className="text-xl font-semibold">V3 React Player</h1>
                <p className="text-sm text-white/50">
                    Open this player with a <code className="bg-white/10 px-2 py-0.5 rounded">?job=JOB_ID</code> query parameter.
                </p>
                <p className="text-xs text-white/30 mt-2">
                    Example: <code className="bg-white/10 px-2 py-0.5 rounded">http://localhost:5173/?job=abc123</code>
                </p>
            </div>
        );
    }

    return (
        <V3Player
            jobId={jobId}
            onClose={() => window.history.back()}
        />
    );
}
