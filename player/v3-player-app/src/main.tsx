import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App';

const params = new URLSearchParams(window.location.search);
const jobId = params.get('job') || params.get('job_id') || '';

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <App jobId={jobId} />
    </StrictMode>
);
