import { useEffect, useMemo, useState } from 'react';
import {
  Activity, ArrowRight, ArrowUpRight, Bell, BriefcaseBusiness, Check, CheckCircle2,
  ChevronDown, CircleHelp, Clock3, Command, Compass, ExternalLink, FileCheck2, FileText,
  Gauge, Globe2, LayoutDashboard, LockKeyhole, Menu, Plus, Search, Settings,
  ShieldCheck, Sparkles, Target, UserRound, WandSparkles, X, Zap, Database,
  Trash2, RefreshCw, AlertCircle, Clock, ToggleLeft, ToggleRight, Bot, Download, FileSpreadsheet, ListChecks,
} from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const POSTING_WINDOWS = [
  { key: '24h', label: 'Past 24 hours', hours: 24 },
  { key: '1d', label: 'Past 1 day', hours: 24 },
  { key: '7d', label: 'Past 7 days', hours: 168 },
  { key: '1m', label: 'Past 1 month', hours: 720 },
];
function getPostingWindow(key) {
  return POSTING_WINDOWS.find(option => option.key === key) || POSTING_WINDOWS[0];
}
const SEARCH_REGIONS = [
  { key: 'global', label: 'Global — all regions' },
  { key: 'india', label: 'India — all states & cities' },
  { key: 'asia', label: 'Asia' },
  { key: 'europe', label: 'Europe' },
  { key: 'americas', label: 'Americas (North, Central & South)' },
  { key: 'middle_east', label: 'Middle East' },
  { key: 'africa', label: 'Africa' },
  { key: 'oceania', label: 'Oceania (Australia & Pacific)' },
  { key: 'custom', label: 'Custom city / country' },
];
const WORK_MODE_OPTIONS = [
  { key: 'remote', label: 'Remote' }, { key: 'hybrid', label: 'Hybrid' },
  { key: 'onsite', label: 'On-site' }, { key: 'unknown', label: 'Not specified' },
];
const EMPLOYMENT_TYPE_OPTIONS = [
  { key: 'full_time', label: 'Full-time / Permanent' }, { key: 'part_time', label: 'Part-time' },
  { key: 'contract_freelance', label: 'Contract / Freelance' }, { key: 'internship', label: 'Internship' },
  { key: 'temporary', label: 'Temporary / Seasonal' }, { key: 'unknown', label: 'Not specified' },
];
const ALL_WORK_MODE_KEYS = WORK_MODE_OPTIONS.map(item => item.key);
const ALL_EMPLOYMENT_TYPE_KEYS = EMPLOYMENT_TYPE_OPTIONS.map(item => item.key);
function regionLabel(key, customLocation = '') {
  if (key === 'custom') return customLocation ? `Custom: ${customLocation}` : 'Custom location';
  return SEARCH_REGIONS.find(item => item.key === key)?.label || 'Global — all regions';
}

function apiErrorMessage(detail, status, fallback = 'Request failed') {
  const render = value => {
    if (value == null) return '';
    if (typeof value === 'string') return value.trim();
    if (Array.isArray(value)) return value.map(render).filter(Boolean).join('; ');
    if (typeof value === 'object') {
      const location = Array.isArray(value.loc)
        ? value.loc.filter(part => part !== 'body' && part !== 'query').join('.')
        : '';
      const message = value.msg || value.message || value.error || value.detail;
      if (message != null && message !== value) {
        const rendered = render(message);
        return [location, rendered].filter(Boolean).join(': ');
      }
      try { return JSON.stringify(value); } catch { return ''; }
    }
    return String(value);
  };
  const message = render(detail);
  return message || `${fallback}${status ? ` (HTTP ${status})` : ''}.`;
}

async function readResponsePayload(response) {
  const raw = await response.text();
  if (!raw) return {};
  try { return JSON.parse(raw); }
  catch { return { detail: raw.slice(0, 500) || `Server returned HTTP ${response.status}` }; }
}
const NAV_ITEMS = [
  { id: 'jobs', label: 'Find & Apply', icon: Compass, tag: 'MAIN' },
  { id: 'applications', label: 'Applications', icon: FileCheck2 },
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
];
const WORKSPACE_ITEMS = [
  { id: 'profile', label: 'My profile', icon: UserRound },
  { id: 'settings', label: 'Settings', icon: Settings },
];
const DEFAULT_PROFILE = {
  full_name: '', years_experience: 0,
  target_titles: 'IT Recruiter, Talent Acquisition Specialist, HR Recruiter',
  skills: '', preferred_locations: 'India, Remote',
  preferred_work_modes: 'Remote, Hybrid, On-site', verified_facts_json: '{}',
  resume_headline: '', profile_summary: '', employment_highlights: '',
  employment_history_json: '[]', education_json: '[]', it_skills_json: '[]',
  projects_json: '[]', online_profiles_json: '[]', work_samples_json: '[]',
  publications_json: '[]', presentations_json: '[]', patents_json: '[]',
  certifications_json: '[]', career_profile_json: '{}', personal_details_json: '{}',
  languages_json: '[]', resume_original_filename: null, resume_uploaded_at: null,
  resume_size_bytes: null, resume_parse_status: 'not_uploaded',
};

function getInitials(name = '') {
  return name.trim().split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0].toUpperCase()).join('') || 'AJ';
}

function profileProgress(profile) {
  const hasArray = key => {
    try { return Array.isArray(JSON.parse(profile[key] || '[]')) && JSON.parse(profile[key] || '[]').length > 0; }
    catch { return false; }
  };
  const checks = [
    Boolean(profile.full_name?.trim()),
    Boolean(profile.resume_original_filename),
    Boolean(profile.resume_headline?.trim() || profile.target_titles?.trim()),
    Boolean(profile.profile_summary?.trim()),
    Boolean(profile.skills?.trim()),
    hasArray('employment_history_json'),
    hasArray('education_json'),
    Boolean(profile.preferred_locations?.trim()),
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

function jobSelectionKey(job) {
  const url = String(job?.source_url || '').trim().split('#')[0].replace(/\/$/, '').toLowerCase();
  if (url) return `url:${url}`;
  return job?.id ? `id:${job.id}` : `title:${String(job?.title || '').toLowerCase()}|${String(job?.company || '').toLowerCase()}`;
}

function toApplicationQueuePayload(job) {
  return {
    job_id: job.id ?? null,
    title: String(job.title || 'Untitled role'),
    company: String(job.company || 'Unknown company'),
    location: String(job.location || 'Not specified'),
    work_mode: String(job.work_mode || 'Unknown'),
    source_url: job.source_url,
    description: String(job.description || '').slice(0, 20000),
    posted_at: job.posted_at || null,
    verified_posting_time: Boolean(job.verified_posting_time),
    match_score: Math.max(0, Math.min(100, Number(job.match_score || 0))),
    matched_keywords: [...(job.matched_keywords || []), ...(job.required_skills || []), ...(job.match_reasons || [])].filter(Boolean).slice(0, 30),
  };
}

function formatPosted(date) {
  if (!date) return 'Posting time not verified';
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return 'Posting time not verified';
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function App() {
  const [health, setHealth] = useState('checking');
  const [jobs, setJobs] = useState([]);
  const [profile, setProfile] = useState(DEFAULT_PROFILE);
  const [message, setMessage] = useState('');
  const [activeView, setActiveView] = useState('jobs');
  const [query, setQuery] = useState('');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [showAddJob, setShowAddJob] = useState(false);
  const [jobDraft, setJobDraft] = useState({ title: '', company: '', location: 'Remote, India', work_mode: 'Remote', source_url: '', description: '', posted_at: '', verified_posting_time: false });
  const [jobMessage, setJobMessage] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);
  const [resumeUploading, setResumeUploading] = useState(false);
  const [resumeDeleting, setResumeDeleting] = useState(false);
  const [resumeMessage, setResumeMessage] = useState('');
  const [resumePreview, setResumePreview] = useState('');
  const [showResumePreview, setShowResumePreview] = useState(false);
  const [sources, setSources] = useState([]);
  const [sourceDraft, setSourceDraft] = useState({ provider: 'greenhouse', company_name: '', board_id: '' });
  const [sourceMessage, setSourceMessage] = useState('');
  const [sourceBusy, setSourceBusy] = useState(false);
  const [discoveryQuery, setDiscoveryQuery] = useState('Talent Acquisition, IT Recruiter, HR Recruiter');
  const [postingWindow, setPostingWindow] = useState('24h');
  const [searchRegion, setSearchRegion] = useState('global');
  const [customLocation, setCustomLocation] = useState('');
  const [selectedWorkModes, setSelectedWorkModes] = useState(ALL_WORK_MODE_KEYS);
  const [selectedEmploymentTypes, setSelectedEmploymentTypes] = useState(ALL_EMPLOYMENT_TYPE_KEYS);
  const [discoveryBusy, setDiscoveryBusy] = useState(false);
  const [discoveryError, setDiscoveryError] = useState('');
  const [discoveryResult, setDiscoveryResult] = useState(null);
  const [includeUnverified, setIncludeUnverified] = useState(true);
  const [applications, setApplications] = useState([]);
  const [analytics, setAnalytics] = useState({ total_applications: 0, submitted: 0, awaiting_review: 0, interviews: 0, offers: 0, rejected: 0, applied_last_7_days: 0, applied_last_30_days: 0, by_status: {}, by_platform: {} });
  const [agentQuery, setAgentQuery] = useState('Talent Acquisition, IT Recruiter, HR Recruiter, Technical Recruiter — India and global roles');
  const [agentBusy, setAgentBusy] = useState(false);
  const [agentAutoApply, setAgentAutoApply] = useState(false);
  const [agentReport, setAgentReport] = useState(null);
  const [agentError, setAgentError] = useState('');
  const [applicationActionMessage, setApplicationActionMessage] = useState('');
  const [selectedQueueJobs, setSelectedQueueJobs] = useState([]);
  const [queueBusy, setQueueBusy] = useState(false);
  const [queueMessage, setQueueMessage] = useState('');
  const [applicationBusyId, setApplicationBusyId] = useState(null);
  const [autoSubmitEnabled, setAutoSubmitEnabled] = useState(false);
  const [automationNote, setAutomationNote] = useState('');

  async function loadJobs() {
    try {
      const [jobsResponse, matchesResponse] = await Promise.all([
        fetch(`${API}/api/jobs`), fetch(`${API}/api/jobs/matches`),
      ]);
      if (!jobsResponse.ok) return;
      const saved = await jobsResponse.json();
      const matches = matchesResponse.ok ? await matchesResponse.json() : [];
      const matchById = new Map(matches.map(item => [item.job.id, item]));
      setJobs(saved.map(job => {
        const match = matchById.get(job.id);
        return match ? {
          ...job,
          match_score: match.match_score,
          rule_based_score: match.rule_based_score,
          semantic_fit_score: match.semantic_fit_score,
          semantic_similarity: match.semantic_similarity,
          match_method: match.match_method,
          matching_note: match.matching_note,
          score_breakdown: match.score_breakdown,
          matched_keywords: match.matched_keywords,
          match_reasons: match.reasons,
        } : job;
      }));
    } catch { /* The health indicator explains API connectivity. */ }
  }

  async function loadApplications() {
    try {
      const [appsResponse, analyticsResponse, automationResponse] = await Promise.all([
        fetch(`${API}/api/applications`), fetch(`${API}/api/analytics`), fetch(`${API}/api/automation/settings`),
      ]);
      if (appsResponse.ok) setApplications(await appsResponse.json());
      if (analyticsResponse.ok) setAnalytics(await analyticsResponse.json());
      if (automationResponse.ok) {
        const automation = await automationResponse.json();
        setAutoSubmitEnabled(Boolean(automation.auto_submit_enabled));
        setAutomationNote(automation.note || '');
      }
    } catch { /* Offline state is shown in the top bar. */ }
  }

  async function runJobAgent(event) {
    event?.preventDefault();
    setAgentBusy(true);
    setAgentError('');
    setAgentReport(null);
    try {
      const response = await fetch(`${API}/api/agent/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: agentQuery, hours: getPostingWindow(postingWindow).hours, min_match_score: 30,
          max_applications: 10, include_unverified: false, prepare_applications: true,
          auto_apply: agentAutoApply, region: searchRegion, custom_location: customLocation,
          work_modes: selectedWorkModes, employment_types: selectedEmploymentTypes,
        }),
      });
      const data = await readResponsePayload(response);
      if (!response.ok) throw new Error(apiErrorMessage(data.detail ?? data.message ?? data, response.status, 'The job agent could not complete this run'));
      setAgentReport({ ...data, posting_window_key: postingWindow, region_key: searchRegion, custom_location: customLocation, work_modes: selectedWorkModes, employment_types: selectedEmploymentTypes });
      await Promise.all([loadJobs(), loadApplications()]);
    } catch (error) {
      setAgentError(error.message || 'Could not reach the job agent. Check the backend and configured job boards.');
    } finally {
      setAgentBusy(false);
    }
  }

  async function updateApplicationStatus(id, status) {
    setApplicationBusyId(id);
    try {
      const response = await fetch(`${API}/api/applications/${id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(data.detail, response.status, 'Could not update application status'));
      setApplications(previous => previous.map(item => item.id === id ? data : item));
      await loadApplications();
    } catch (error) {
      setAgentError(error.message || 'Could not update application status.');
    } finally { setApplicationBusyId(null); }
  }

  async function generateAnswersForApplication(id) {
    setApplicationBusyId(id);
    setAgentError('');
    try {
      const questions = [
        'Tell us about yourself.',
        'Why are you interested in this role?',
        'Which skills make you a good fit for this position?',
        'What is your notice period?',
        'What are your salary expectations?',
      ];
      const response = await fetch(`${API}/api/applications/${id}/answers/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ questions }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(data.detail, response.status, 'Could not draft screening answers'));
      setApplications(previous => previous.map(item => item.id === id ? data : item));
    } catch (error) { setAgentError(error.message || 'Could not draft answers.'); }
    finally { setApplicationBusyId(null); }
  }

  async function reviewScreeningAnswer(id, answerIndex, answer, status = 'verified') {
    setApplicationBusyId(id);
    setAgentError('');
    try {
      const response = await fetch(`${API}/api/applications/${id}/answers/${answerIndex}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer, status }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(data.detail, response.status, 'Could not save screening answer'));
      setApplications(previous => previous.map(item => item.id === id ? data : item));
      return true;
    } catch (error) {
      setAgentError(error.message || 'Could not save screening answer.');
      return false;
    } finally { setApplicationBusyId(null); }
  }

  async function fillApplicationForm(id, confirmSubmit = false) {
    setApplicationBusyId(id);
    setAgentError('');
    try {
      const response = await fetch(`${API}/api/applications/${id}/browser-fill`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm_submit: confirmSubmit }),
      });
      const data = await readResponsePayload(response);
      if (!response.ok) throw new Error(apiErrorMessage(data.detail ?? data.message ?? data, response.status, 'Browser application workflow could not start'));
      setAgentReport({ message: data.message, submitted: data.submitted ? 1 : 0, needs_review: data.missing_required?.length || 0, warnings: data.missing_required || [] });
      await loadApplications();
    } catch (error) { setAgentError(error.message || 'Could not open the supported application form.'); }
    finally { setApplicationBusyId(null); }
  }

  async function analyzeJob(job) {
    if (!job?.id) throw new Error('Save this listing to your job tracker before running the detailed analysis.');
    const response = await fetch(`${API}/api/jobs/${job.id}/analysis`, { method: 'POST' });
    const data = await readResponsePayload(response);
    if (!response.ok) throw new Error(apiErrorMessage(data.detail ?? data.message ?? data, response.status, 'Could not analyze this job'));
    return data;
  }

  async function prepareApplicationFromJob(job, analysis = null, options = {}) {
    const { navigateToApplications = true } = options;
    if (!job?.id) throw new Error('This listing is not saved yet. Run a search with a verified posting or save it manually first.');
    setAgentError('');
    setApplicationBusyId(job.id);
    try {
      let applicationRecord = null;
      const createResponse = await fetch(`${API}/api/applications/from-job/${job.id}`, { method: 'POST' });
      const createData = await readResponsePayload(createResponse);
      if (createResponse.ok) {
        applicationRecord = createData;
      } else if (createResponse.status === 409) {
        const existingResponse = await fetch(`${API}/api/applications`);
        const existingItems = existingResponse.ok ? await existingResponse.json() : [];
        applicationRecord = existingItems.find(item => item.source_url === job.source_url) || null;
        if (!applicationRecord) throw new Error(apiErrorMessage(createData.detail, createResponse.status, 'This job already exists in application history, but its record could not be loaded'));
      } else {
        throw new Error(apiErrorMessage(createData.detail ?? createData.message ?? createData, createResponse.status, 'Could not prepare the application'));
      }

      const questions = analysis?.suggested_screening_questions?.length
        ? analysis.suggested_screening_questions.slice(0, 12)
        : [
            `Tell us about your experience relevant to the ${job.title} role.`,
            `Why are you interested in working at ${job.company}?`,
            'Which skills from your profile best match this position?',
            'Describe a relevant achievement from your professional experience.',
          ];
      const answerResponse = await fetch(`${API}/api/applications/${applicationRecord.id}/answers/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ questions }),
      });
      const answerData = await readResponsePayload(answerResponse);
      if (answerResponse.ok) applicationRecord = answerData;
      await loadApplications();
      setAgentReport({
        message: `Application preparation saved for ${job.title} at ${job.company}. Review all answer drafts before applying.`,
        warnings: [
          ...(answerResponse.ok ? [] : ['The application record was saved, but screening-answer generation failed: ' + apiErrorMessage(answerData.detail ?? answerData, answerResponse.status, 'unknown error')]),
          ...(!profile.resume_original_filename ? ['No resume file is attached to the profile yet. Upload one before trying to fill an application form.'] : []),
          'No application was submitted by this action. Open the original listing and review every answer first.',
        ],
        submitted: 0,
      });
      if (navigateToApplications) {
        setActiveView('applications');
        setMobileNavOpen(false);
      }
      return applicationRecord;
    } catch (error) {
      setAgentError(error.message || 'Could not prepare the application.');
      throw error;
    } finally {
      setApplicationBusyId(null);
    }
  }


  async function getOrCreateApplicationRecord(job) {
    if (!job?.id) throw new Error('This listing is not saved in the tracker yet. Open it manually or search again to save it first.');
    const createResponse = await fetch(`${API}/api/applications/from-job/${job.id}`, { method: 'POST' });
    const createData = await readResponsePayload(createResponse);
    if (createResponse.ok) return createData;
    if (createResponse.status === 409) {
      const existingResponse = await fetch(`${API}/api/applications`);
      const existingItems = existingResponse.ok ? await existingResponse.json() : [];
      const normalizeUrl = value => String(value || '').split('#')[0].replace(/\/$/, '').toLowerCase();
      const existing = existingItems.find(item => normalizeUrl(item.source_url) === normalizeUrl(job.source_url));
      if (existing) return existing;
    }
    throw new Error(apiErrorMessage(createData.detail ?? createData.message ?? createData, createResponse.status, 'Could not create the application record'));
  }

  async function ensureApplicationRecordForLead(job) {
    if (job?.id) return getOrCreateApplicationRecord(job);
    const response = await fetch(`${API}/api/applications/queue`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jobs: [toApplicationQueuePayload(job)] }),
    });
    const data = await readResponsePayload(response);
    if (!response.ok) throw new Error(apiErrorMessage(data.detail ?? data.message ?? data, response.status, 'Could not add this job to Application History'));
    const item = data.items?.[0];
    if (!item?.application_id) throw new Error(item?.message || 'The job opened, but no application record was created.');
    const recordsResponse = await fetch(`${API}/api/applications`);
    const records = recordsResponse.ok ? await recordsResponse.json() : [];
    const record = records.find(candidate => candidate.id === item.application_id);
    if (!record) throw new Error('The job was queued but its Application History record could not be loaded.');
    return record;
  }

  async function manualApplyToJob(job) {
    if (!job?.source_url) {
      setApplicationActionMessage('This job does not have a valid application link.');
      return;
    }
    // Open synchronously from the click event so browsers are less likely to block it.
    window.open(job.source_url, '_blank', 'noopener,noreferrer');
    setApplicationActionMessage('Opening the employer listing and recording it in Application History…');
    try {
      const record = await ensureApplicationRecordForLead(job);
      if (!['submitted', 'submitted_unconfirmed', 'interview', 'offer', 'rejected', 'withdrawn'].includes(record.status)) {
        await fetch(`${API}/api/applications/${record.id}`, {
          method: 'PATCH', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'needs_manual_action', notes: 'Employer application opened in a new tab. Update the status after completing the application. Opening the listing does not confirm submission.' }),
        });
      }
      await loadApplications();
      setApplicationActionMessage(`Opened ${job.title} at ${job.company}. The role is in Application History; mark it Submitted only after finishing the employer's form.`);
    } catch (error) {
      setApplicationActionMessage(`The listing was opened, but history could not be updated: ${error.message || 'unknown error'}`);
    }
  }

  async function autoApplyToJob(job, analysis = null) {
    setApplicationActionMessage('');
    if (!job?.id) {
      setApplicationActionMessage('This lead is not saved as a job record yet. Use Apply manually, or rerun discovery with verified listings enabled.');
      return;
    }
    if (!profile.resume_original_filename) {
      setApplicationActionMessage('Upload your resume first. You will be taken to My Profile.');
      navigate('profile');
      setMessage('Upload your resume in the Resume section, then return to Find & Apply.');
      return;
    }
    try {
      const applicationRecord = await prepareApplicationFromJob(job, analysis, { navigateToApplications: false });
      if (!applicationRecord?.id) throw new Error('The application record could not be loaded.');
      if (!autoSubmitEnabled) {
        setAgentReport({
          message: `Application prepared for ${job.title} at ${job.company}. Automatic submission is currently disabled.`,
          submitted: 0,
          warnings: ['Your application and screening-answer drafts are saved. Review and verify every answer in Application History. To enable supported automatic submission, configure AUTO_SUBMIT_ENABLED=true only after reviewing site rules and risks. No application was submitted.'],
        });
        await loadApplications();
        setActiveView('applications');
        setMobileNavOpen(false);
        return;
      }
      setApplicationBusyId(job.id);
      const response = await fetch(`${API}/api/applications/${applicationRecord.id}/browser-fill`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm_submit: true }),
      });
      const data = await readResponsePayload(response);
      if (!response.ok) throw new Error(apiErrorMessage(data.detail ?? data.message ?? data, response.status, 'Automatic application could not proceed'));
      setAgentReport({
        message: data.message || 'The supported application workflow finished.',
        submitted: data.submitted ? 1 : 0,
        needs_review: data.missing_required?.length || 0,
        warnings: [...(data.missing_required || []), ...(data.needs_human_verification ? ['Human verification is required. Complete it manually; the agent will not bypass it.'] : [])],
      });
      await loadApplications();
      setActiveView('applications');
      setMobileNavOpen(false);
    } catch (error) {
      setApplicationActionMessage(error.message || 'Automatic application could not proceed.');
    } finally {
      setApplicationBusyId(null);
    }
  }

  function toggleQueueJob(job) {
    if (!job?.source_url) return;
    const key = jobSelectionKey(job);
    const alreadySelected = selectedQueueJobs.some(item => jobSelectionKey(item) === key);
    setQueueMessage('');
    if (alreadySelected) {
      setSelectedQueueJobs(selectedQueueJobs.filter(item => jobSelectionKey(item) !== key));
      return;
    }
    if (selectedQueueJobs.length >= 50) {
      setQueueMessage('You can prepare up to 50 jobs in one batch. Prepare or clear the current selection first.');
      return;
    }
    setSelectedQueueJobs([...selectedQueueJobs, job]);
  }

  function selectVisibleQueueJobs(candidates) {
    const unique = new Map();
    for (const job of candidates || []) {
      if (job?.source_url) unique.set(jobSelectionKey(job), job);
    }
    const chosen = [...unique.values()].slice(0, 50);
    setSelectedQueueJobs(chosen);
    setQueueMessage(unique.size > 50 ? `Selected the first 50 of ${unique.size} visible leads. The queue limit is 50 per batch.` : `${chosen.length} visible leads selected.`);
  }

  async function prepareSelectedApplications() {
    if (!selectedQueueJobs.length || queueBusy) return;
    setQueueBusy(true);
    setQueueMessage('');
    setAgentError('');
    try {
      const jobsPayload = selectedQueueJobs.map(toApplicationQueuePayload);
      const response = await fetch(`${API}/api/applications/queue`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jobs: jobsPayload }),
      });
      const data = await readResponsePayload(response);
      if (!response.ok) throw new Error(apiErrorMessage(data.detail ?? data.message ?? data, response.status, 'Could not prepare selected applications'));
      const warnings = (data.items || []).filter(item => item.action === 'failed').map(item => `${item.title} at ${item.company}: ${item.message}`);
      setAgentReport({
        message: data.message || `Prepared ${data.created || 0} applications for review.`,
        submitted: 0,
        needs_review: data.created || 0,
        warnings: [
          'This action only creates or reuses Application History records. No applications were submitted.',
          ...(warnings.length ? warnings : []),
          ...((data.items || []).some(item => item.action === 'reused') ? ['Previously tracked records were reused; existing statuses and answers were preserved.'] : []),
        ],
      });
      setQueueMessage(data.message || 'Application queue updated.');
      setSelectedQueueJobs([]);
      await Promise.all([loadApplications(), loadJobs()]);
      if ((data.created || 0) + (data.reused || 0) > 0) {
        setActiveView('applications');
        setMobileNavOpen(false);
      }
    } catch (error) {
      setQueueMessage(error.message || 'Could not prepare the selected applications.');
    } finally {
      setQueueBusy(false);
    }
  }

  async function applyManuallyFromHistory(appRecord) {
    if (!appRecord?.source_url) {
      setAgentError('This application record has no valid original job URL.');
      return;
    }
    // Open synchronously from the user click; update history separately afterward.
    window.open(appRecord.source_url, '_blank', 'noopener,noreferrer');
    setApplicationBusyId(appRecord.id);
    setAgentError('');
    try {
      const protectedStatuses = new Set(['submitted', 'submitted_unconfirmed', 'interview', 'offer', 'rejected', 'withdrawn']);
      const notePrefix = String(appRecord.notes || '').slice(0, 4200);
      const noteSuffix = protectedStatuses.has(appRecord.status)
        ? `Original job listing opened for review on ${new Date().toLocaleString()}. Status was preserved as ${appRecord.status}.`
        : `Original job listing opened on ${new Date().toLocaleString()}. Complete the employer form manually, then update this record to Submitted. Opening a link does not confirm submission.`;
      const payload = protectedStatuses.has(appRecord.status)
        ? { notes: `${notePrefix}${notePrefix ? '\n' : ''}${noteSuffix}`.slice(0, 5000) }
        : { status: 'needs_manual_action', notes: `${notePrefix}${notePrefix ? '\n' : ''}${noteSuffix}`.slice(0, 5000) };
      const response = await fetch(`${API}/api/applications/${appRecord.id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const data = await readResponsePayload(response);
      if (!response.ok) throw new Error(apiErrorMessage(data.detail, response.status, 'Could not update application history'));
      setApplications(previous => previous.map(item => item.id === data.id ? data : item));
      setAgentReport({ message: `Opened ${appRecord.title} at ${appRecord.company}. The record has not been marked as submitted.`, submitted: 0, warnings: ['Finish the employer application in the opened tab. Return to Application History and set the status to Submitted only after you complete the form.'] });
      await loadApplications();
    } catch (error) {
      setAgentError(`The job listing opened, but Application History could not be updated: ${error.message || 'unknown error'}`);
    } finally {
      setApplicationBusyId(null);
    }
  }

  useEffect(() => {
    fetch(`${API}/api/health`)
      .then(response => { if (!response.ok) throw new Error('API unavailable'); return response.json(); })
      .then(() => setHealth('online'))
      .catch(() => setHealth('offline'));
    loadJobs();
    loadSources();
    loadApplications();
    fetch(`${API}/api/profile`)
      .then(response => response.ok ? response.json() : null)
      .then(data => {
        if (data) {
          setProfile({ ...DEFAULT_PROFILE, ...data });
          if (data.target_titles) setDiscoveryQuery(data.target_titles);
          loadJobs();
        }
      })
      .catch(() => {});
  }, []);

  async function loadSources() {
    try {
      const response = await fetch(`${API}/api/sources`);
      if (response.ok) setSources(await response.json());
    } catch { /* The API status already reports local connectivity. */ }
  }

  async function addSource(event) {
    event.preventDefault();
    setSourceBusy(true);
    setSourceMessage('');
    try {
      const response = await fetch(`${API}/api/sources`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sourceDraft),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(data.detail, response.status, 'Could not add source'));
      setSources(previous => [data, ...previous]);
      setSourceDraft({ provider: sourceDraft.provider, company_name: '', board_id: ['arbeitnow', 'remoteok', 'jobicy', 'himalayas', 'brave', 'jobspy'].includes(sourceDraft.provider) ? 'default' : sourceDraft.provider === 'adzuna' ? 'in' : '' });
      setSourceMessage('Source added. You can search this public job board now.');
    } catch (error) {
      setSourceMessage(error.message || 'Could not add source. Check the API connection.');
    } finally {
      setSourceBusy(false);
    }
  }

  async function removeSource(sourceId) {
    try {
      const response = await fetch(`${API}/api/sources/${sourceId}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Could not remove source');
      setSources(previous => previous.filter(source => source.id !== sourceId));
      setSourceMessage('Source removed.');
    } catch (error) {
      setSourceMessage(error.message || 'Could not remove source.');
    }
  }

  async function toggleSource(source) {
    try {
      const response = await fetch(`${API}/api/sources/${source.id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: !source.enabled }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(data.detail, response.status, 'Could not update source'));
      setSources(previous => previous.map(item => item.id === data.id ? data : item));
    } catch (error) {
      setSourceMessage(error.message || 'Could not update source.');
    }
  }

  async function runDiscovery(event) {
    event?.preventDefault();
    setDiscoveryBusy(true);
    setDiscoveryError('');
    setDiscoveryResult(null);
    setSelectedQueueJobs([]);
    setQueueMessage('');
    try {
      const response = await fetch(`${API}/api/discovery/search`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: discoveryQuery, hours: getPostingWindow(postingWindow).hours, include_unverified: includeUnverified,
          region: searchRegion, custom_location: customLocation, work_modes: selectedWorkModes,
          employment_types: selectedEmploymentTypes,
        }),
      });
      const data = await readResponsePayload(response);
      if (!response.ok) throw new Error(apiErrorMessage(data.detail ?? data.message ?? data, response.status, 'Job discovery failed'));
      setDiscoveryResult({ ...data, posting_window_key: postingWindow, region_key: searchRegion, custom_location: customLocation, work_modes: selectedWorkModes, employment_types: selectedEmploymentTypes });
      if (data.fresh_jobs?.length) {
        setJobs(previous => {
          const byId = new Map(previous.map(job => [job.id, job]));
          for (const job of data.fresh_jobs) if (job.id) byId.set(job.id, { ...byId.get(job.id), ...job });
          return [...byId.values()].sort((a, b) => new Date(b.created_at || b.posted_at || 0) - new Date(a.created_at || a.posted_at || 0));
        });
      }
      await loadJobs();
    } catch (error) {
      setDiscoveryError(error.message || 'Could not reach the discovery API.');
    } finally {
      setDiscoveryBusy(false);
    }
  }

  const completion = useMemo(() => profileProgress(profile), [profile]);
  const filteredJobs = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return jobs;
    return jobs.filter(job => [job.title, job.company, job.location, job.description].some(value => String(value || '').toLowerCase().includes(normalized)));
  }, [jobs, query]);

  function navigate(view) {
    setActiveView(view);
    setMobileNavOpen(false);
    setMessage('');
  }

  async function saveProfile(event) {
    event.preventDefault();
    setSavingProfile(true);
    setMessage('');
    try {
      const response = await fetch(`${API}/api/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
      });
      if (!response.ok) throw new Error('Could not save profile');
      setProfile({ ...DEFAULT_PROFILE, ...await response.json() });
      setMessage('Your profile has been saved to this device.');
      loadJobs();
    } catch {
      setMessage('Could not reach the API. Start the backend and try again.');
    } finally {
      setSavingProfile(false);
    }
  }

  async function uploadResume(file) {
    if (!file) return false;
    setResumeMessage('');
    setResumePreview('');
    setShowResumePreview(false);
    if (file.size > 2 * 1024 * 1024) {
      setResumeMessage('Resume must be 2 MB or smaller.');
      return false;
    }
    const formData = new FormData();
    formData.append('file', file);
    setResumeUploading(true);
    try {
      const response = await fetch(`${API}/api/profile/resume`, { method: 'POST', body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(data.detail, response.status, 'Could not upload resume'));
      setResumeMessage(`Uploaded ${data.filename} · ${(data.size_bytes / 1024).toFixed(0)} KB. ${data.extracted_characters ? `${data.extracted_characters.toLocaleString()} characters extracted.` : data.parse_status === 'uploaded_no_selectable_text' ? 'No selectable text found; this may be a scanned PDF.' : 'File saved; text extraction is unavailable for this format.'}`);
      setResumePreview(data.extracted_text_preview || '');
      const profileResponse = await fetch(`${API}/api/profile`);
      if (profileResponse.ok) setProfile({ ...DEFAULT_PROFILE, ...await profileResponse.json() });
      return true;
    } catch (error) {
      setResumeMessage(error.message || 'Could not upload resume. Check the API connection.');
      return false;
    } finally {
      setResumeUploading(false);
    }
  }

  async function deleteResume() {
    if (!profile.resume_original_filename) return;
    setResumeDeleting(true);
    setResumeMessage('');
    try {
      const response = await fetch(`${API}/api/profile/resume`, { method: 'DELETE' });
      const data = response.status === 204 ? null : await response.json();
      if (!response.ok) throw new Error(data?.detail || 'Could not remove resume');
      const profileResponse = await fetch(`${API}/api/profile`);
      if (profileResponse.ok) setProfile({ ...DEFAULT_PROFILE, ...await profileResponse.json() });
      setResumePreview('');
      setShowResumePreview(false);
      setResumeMessage('Resume removed from local storage.');
    } catch (error) {
      setResumeMessage(error.message || 'Could not remove resume.');
    } finally {
      setResumeDeleting(false);
    }
  }

  async function loadResumeText() {
    try {
      const response = await fetch(`${API}/api/profile/resume/text`);
      const data = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(data.detail, response.status, 'Could not read resume text'));
      setResumePreview(data.text || '');
      setShowResumePreview(true);
    } catch (error) {
      setResumeMessage(error.message || 'Could not read resume text.');
    }
  }

  async function addJob(event) {
    event.preventDefault();
    setJobMessage('');
    try {
      const payload = { ...jobDraft, posted_at: jobDraft.posted_at || null };
      const response = await fetch(`${API}/api/jobs`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(data.detail, response.status, 'Could not save job'));
      setJobs(previous => [data, ...previous]);
      setJobDraft({ title: '', company: '', location: 'Remote, India', work_mode: 'Remote', source_url: '', description: '', posted_at: '', verified_posting_time: false });
      setShowAddJob(false);
      setJobMessage('Job saved to your local tracker.');
    } catch (error) {
      setJobMessage(error.message || 'Could not save job. Check the URL and API connection.');
    }
  }

  const viewTitle = {
    overview: ['Overview', 'Your job search, all in one place.'],
    jobs: ['Find & apply', 'Search jobs, attach your CV, compare match scores, then choose manual or supported automatic application.'],
    applications: ['Application History & Analytics', 'Track every application attempt, review screening answers, and export your history to Excel.'],
    profile: ['My profile', 'Give your assistant reliable facts to work from.'],
    settings: ['Settings', 'Choose how AI Job Hunter works on your machine.'],
  }[activeView];

  return (
    <div className={`app-shell ${activeView === 'jobs' && selectedQueueJobs.length > 0 ? 'has-queue-sticky' : ''}`}>
      {mobileNavOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />}
      <aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-brand">
          <div className="brand-mark"><WandSparkles size={20} strokeWidth={2.2} /></div>
          <div className="brand-copy"><span>job<span className="brand-accent">hunter</span></span><small>YOUR CAREER COPILOT</small></div>
          <button className="icon-button sidebar-close" onClick={() => setMobileNavOpen(false)} aria-label="Close menu"><X size={18}/></button>
        </div>

        <div className="workspace-select">
          <div className="workspace-avatar"><Sparkles size={16}/></div>
          <div className="workspace-copy"><strong>Personal workspace</strong><span>Local environment</span></div>
          <ChevronDown size={15} className="muted-icon"/>
        </div>

        <div className="nav-caption">WORKSPACE</div>
        <nav className="nav-list" aria-label="Main navigation">
          {NAV_ITEMS.map(item => {
            const Icon = item.icon;
            return <button key={item.id} className={`nav-item ${activeView === item.id ? 'active' : ''}`} onClick={() => navigate(item.id)}>
              <Icon size={18}/><span>{item.label}</span>{item.tag && <span className="nav-tag">{item.tag}</span>}
            </button>;
          })}
        </nav>
        <div className="nav-caption nav-caption-spaced">PREFERENCES</div>
        <nav className="nav-list" aria-label="Preferences">
          {WORKSPACE_ITEMS.map(item => {
            const Icon = item.icon;
            return <button key={item.id} className={`nav-item ${activeView === item.id ? 'active' : ''}`} onClick={() => navigate(item.id)}><Icon size={18}/><span>{item.label}</span></button>;
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-tip">
            <div className="tip-spark"><Sparkles size={16}/></div>
            <strong>Small steps. Big moves.</strong>
            <p>Complete your profile to make future job matches more relevant.</p>
            <button onClick={() => navigate('profile')}>Improve profile <ArrowRight size={14}/></button>
          </div>
          <div className="sidebar-footer-row"><span className={`connection-dot ${health}`}/><span>{health === 'online' ? 'Local API connected' : health === 'checking' ? 'Connecting to local API…' : 'Local API offline'}</span><button className="help-button" title="About this project" onClick={() => navigate('settings')}><CircleHelp size={16}/></button></div>
          <div className="sidebar-user"><div className="user-avatar">{profile.photo_original_filename ? <img src={`${API}/api/profile/photo?v=${encodeURIComponent(profile.photo_uploaded_at || '')}`} alt="Profile"/> : getInitials(profile.full_name)}</div><div className="user-copy"><strong>{profile.full_name || 'Your profile'}</strong><span>Personal account</span></div><button className="icon-button user-more" onClick={() => navigate('profile')} aria-label="Edit profile"><ChevronDown size={16}/></button></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left"><button className="icon-button mobile-menu" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation"><Menu size={20}/></button><div className="breadcrumbs"><span>Workspace</span><span className="breadcrumb-sep">/</span><strong>{viewTitle[0]}</strong></div></div>
          <div className="topbar-actions">
            <label className="global-search"><Search size={16}/><input aria-label="Search tracked jobs" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search your workspace…"/><kbd><Command size={11}/> K</kbd></label>
            <div className={`top-api-status ${health}`}><span className="connection-dot"/>{health === 'online' ? 'Connected' : health === 'checking' ? 'Connecting' : 'Offline'}</div>
            <button className="icon-button notification-button" aria-label="Notifications" title="Notifications are not enabled in this version"><Bell size={18}/><i/></button>
            <button className="top-avatar" title="Open profile" onClick={() => navigate('profile')}>{profile.photo_original_filename ? <img src={`${API}/api/profile/photo?v=${encodeURIComponent(profile.photo_uploaded_at || '')}`} alt="Profile"/> : getInitials(profile.full_name)}</button>
          </div>
        </header>

        <div className="page-content">
          <div className="page-title-row"><div><div className="section-overline">PERSONAL WORKSPACE <span className="overline-dot"/> LOCAL-FIRST</div><h1>{activeView === 'overview' ? <>Good to see you{profile.full_name ? `, ${profile.full_name.split(' ')[0]}` : ''}<span className="title-period">.</span></> : viewTitle[0]}</h1><p>{viewTitle[1]}</p></div>{activeView === 'jobs' && <button className="button button-primary" onClick={() => setShowAddJob(true)}><Plus size={17}/> Add a job</button>}</div>

          {activeView === 'overview' && <OverviewView jobs={jobs} profile={profile} completion={completion} navigate={navigate} health={health} agentQuery={agentQuery} setAgentQuery={setAgentQuery} agentBusy={agentBusy} agentAutoApply={agentAutoApply} setAgentAutoApply={setAgentAutoApply} runJobAgent={runJobAgent} agentReport={agentReport} agentError={agentError} postingWindow={postingWindow} setPostingWindow={setPostingWindow} searchRegion={searchRegion} setSearchRegion={setSearchRegion} customLocation={customLocation} setCustomLocation={setCustomLocation} selectedWorkModes={selectedWorkModes} setSelectedWorkModes={setSelectedWorkModes} selectedEmploymentTypes={selectedEmploymentTypes} setSelectedEmploymentTypes={setSelectedEmploymentTypes} />}
          {activeView === 'jobs' && <JobsView jobs={filteredJobs} query={query} setQuery={setQuery} openAdd={() => setShowAddJob(true)} jobMessage={jobMessage} sources={sources} sourceDraft={sourceDraft} setSourceDraft={setSourceDraft} sourceMessage={sourceMessage} sourceBusy={sourceBusy} addSource={addSource} removeSource={removeSource} toggleSource={toggleSource} discoveryQuery={discoveryQuery} setDiscoveryQuery={setDiscoveryQuery} discoveryBusy={discoveryBusy} discoveryError={discoveryError} discoveryResult={discoveryResult} includeUnverified={includeUnverified} setIncludeUnverified={setIncludeUnverified} runDiscovery={runDiscovery} postingWindow={postingWindow} setPostingWindow={setPostingWindow} searchRegion={searchRegion} setSearchRegion={setSearchRegion} customLocation={customLocation} setCustomLocation={setCustomLocation} selectedWorkModes={selectedWorkModes} setSelectedWorkModes={setSelectedWorkModes} selectedEmploymentTypes={selectedEmploymentTypes} setSelectedEmploymentTypes={setSelectedEmploymentTypes} onAnalyzeJob={analyzeJob} onPrepareApplication={prepareApplicationFromJob} onManualApply={manualApplyToJob} onAutoApply={autoApplyToJob} applicationBusyId={applicationBusyId} profile={profile} navigate={navigate} uploadResume={uploadResume} resumeUploading={resumeUploading} resumeMessage={resumeMessage} autoSubmitEnabled={autoSubmitEnabled} applicationActionMessage={applicationActionMessage} selectedQueueJobs={selectedQueueJobs} onToggleQueueJob={toggleQueueJob} onSelectAllQueueJobs={selectVisibleQueueJobs} onClearQueueJobs={() => { setSelectedQueueJobs([]); setQueueMessage('Selection cleared.'); }} queueSelectedApplications={prepareSelectedApplications} queueBusy={queueBusy} queueMessage={queueMessage} />}
          {activeView === 'applications' && <ApplicationsView applications={applications} analytics={analytics} navigate={navigate} updateStatus={updateApplicationStatus} generateAnswers={generateAnswersForApplication} reviewAnswer={reviewScreeningAnswer} fillForm={fillApplicationForm} applicationBusyId={applicationBusyId} autoSubmitEnabled={autoSubmitEnabled} automationNote={automationNote} agentError={agentError} setAgentError={setAgentError} agentReport={agentReport} onApplyManually={applyManuallyFromHistory} />}
          {activeView === 'profile' && <ProfileView profile={profile} setProfile={setProfile} saveProfile={saveProfile} saving={savingProfile} message={message} completion={completion} uploadResume={uploadResume} resumeUploading={resumeUploading} deleteResume={deleteResume} resumeDeleting={resumeDeleting} resumeMessage={resumeMessage} resumePreview={resumePreview} showResumePreview={showResumePreview} setShowResumePreview={setShowResumePreview} loadResumeText={loadResumeText} />}
          {activeView === 'settings' && <SettingsView health={health} autoSubmitEnabled={autoSubmitEnabled} automationNote={automationNote} />}

          <footer className="page-footer"><span>© 2026 AI Job Hunter <span className="footer-dot">·</span> Open source under MIT</span><span><ShieldCheck size={13}/> Your data stays on this device in local mode</span></footer>
        </div>
      </main>

      {activeView === 'jobs' && discoveryResult && selectedQueueJobs.length > 0 && <div className="queue-sticky-action" role="region" aria-label="Selected job application queue">
        <div className="queue-sticky-copy"><strong>{selectedQueueJobs.length} job{selectedQueueJobs.length === 1 ? '' : 's'} selected</strong><span>Prepare application drafts for review. Nothing will be submitted by this action.</span></div>
        <div className="queue-sticky-buttons"><button type="button" className="button button-secondary" onClick={() => { setSelectedQueueJobs([]); setQueueMessage('Selection cleared.'); }} disabled={queueBusy}>Clear selection</button><button type="button" className="button button-primary" onClick={prepareSelectedApplications} disabled={queueBusy}>{queueBusy ? <><RefreshCw size={15} className="spin-icon"/> Preparing…</> : <><ListChecks size={16}/> Prepare selected ({selectedQueueJobs.length})</>}</button></div>
      </div>}

      {showAddJob && <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setShowAddJob(false); }}><section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="add-job-title"><div className="modal-heading"><div><span className="section-overline">YOUR SHORTLIST</span><h2 id="add-job-title">Add a job to track</h2></div><button className="icon-button" onClick={() => setShowAddJob(false)} aria-label="Close"><X size={18}/></button></div><p className="modal-copy">Save a vacancy you found elsewhere. Discovered listings are added to your tracker automatically when their posting time is verified.</p><form className="profile-form modal-form" onSubmit={addJob}><div className="field-grid"><label>Job title<input required value={jobDraft.title} onChange={e => setJobDraft({...jobDraft, title: e.target.value})} placeholder="Talent Acquisition Specialist"/></label><label>Company<input required value={jobDraft.company} onChange={e => setJobDraft({...jobDraft, company: e.target.value})} placeholder="Company name"/></label></div><div className="field-grid"><label>Location<input value={jobDraft.location} onChange={e => setJobDraft({...jobDraft, location: e.target.value})} placeholder="Remote, India"/></label><label>Work mode<select value={jobDraft.work_mode} onChange={e => setJobDraft({...jobDraft, work_mode: e.target.value})}><option>Remote</option><option>Hybrid</option><option>On-site</option><option>Unknown</option></select></label></div><label>Application / job URL<input type="url" required value={jobDraft.source_url} onChange={e => setJobDraft({...jobDraft, source_url: e.target.value})} placeholder="https://company.com/careers/job-id"/></label><label>Job description <span className="optional-label">Optional</span><textarea rows="3" value={jobDraft.description} onChange={e => setJobDraft({...jobDraft, description: e.target.value})} placeholder="Paste key responsibilities or requirements…"/></label><label>Posting date and time <span className="optional-label">Optional</span><input type="datetime-local" value={jobDraft.posted_at} onChange={e => setJobDraft({...jobDraft, posted_at: e.target.value})}/></label><label className="checkbox-field"><input type="checkbox" checked={jobDraft.verified_posting_time} onChange={e => setJobDraft({...jobDraft, verified_posting_time: e.target.checked})}/><span>I verified the posting time on the original job page.</span></label>{jobMessage && <div className="inline-alert error-alert">{jobMessage}</div>}<div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setShowAddJob(false)}>Cancel</button><button type="submit" className="button button-primary"><Plus size={16}/> Save job</button></div></form></section></div>}
    </div>
  );
}

function OverviewView({ jobs, profile, completion, navigate, health, agentQuery, setAgentQuery, agentBusy, agentAutoApply, setAgentAutoApply, runJobAgent, agentReport, agentError, postingWindow, setPostingWindow, searchRegion, setSearchRegion, customLocation, setCustomLocation, selectedWorkModes, setSelectedWorkModes, selectedEmploymentTypes, setSelectedEmploymentTypes }) {
  const recentJobs = jobs.slice(0, 3);
  const profileReady = completion === 100;
  return <>
    <section className="welcome-hero">
      <div className="welcome-content"><div className="hero-pill"><span className="pill-star"><Sparkles size={13}/></span> YOUR NEXT CHAPTER STARTS HERE</div><h2>Make your next move<br/><span>count.</span></h2><p>Let’s turn your job search into a clear, confident plan. Start with your profile, then build a shortlist worth your time.</p><div className="welcome-actions"><button className="button button-light" onClick={() => navigate('profile')}>{profileReady ? 'Review my profile' : 'Complete my profile'}<ArrowRight size={16}/></button><button className="hero-text-button" onClick={() => navigate('jobs')}>Explore tracked jobs <ArrowUpRight size={15}/></button></div></div>
      <div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit-core"><div className="orbit-core-inner"><Target size={37}/></div></div><div className="float-card float-match"><span className="float-card-icon"><Sparkles size={14}/></span><div><strong>Better matches</strong><small>Built around you</small></div></div><div className="float-card float-profile"><div className="mini-progress"><svg viewBox="0 0 40 40"><circle cx="20" cy="20" r="15"/><circle className="progress-ring" cx="20" cy="20" r="15" style={{strokeDashoffset: 94.2 - (94.2 * completion / 100)}}/></svg><span>{completion}%</span></div><div><strong>Profile strength</strong><small>{profileReady ? 'All key details added' : 'Room to improve'}</small></div></div><div className="hero-spark spark-a">✦</div><div className="hero-spark spark-b">✧</div></div>
      <div className="hero-bottomline"><span><span className="live-dot"/> A calmer way to job hunt</span><span>Discover <i>·</i> Prepare <i>·</i> Apply</span></div>
    </section>

    <section className="agent-command-panel content-panel">
      <div className="agent-command-heading"><div className="agent-command-icon"><Bot size={21}/></div><div><span className="section-overline">YOUR JOB AGENT</span><h2>Search, match, prepare.</h2><p>Give the agent an instruction. It searches all enabled boards, checks verified recent posts, scores matches, and adds suitable openings to Application History.</p></div><label className="agent-window-picker"><span><Clock3 size={13}/> Posting window</span><select aria-label="Job agent posting window" value={postingWindow} onChange={event => setPostingWindow(event.target.value)}>{POSTING_WINDOWS.map(option => <option key={option.key} value={option.key}>{option.label}</option>)}</select></label></div>
      <form className="agent-command-form" onSubmit={runJobAgent}><label htmlFor="agent-instruction">What should I search for?</label><div className="agent-command-input-row"><input id="agent-instruction" value={agentQuery} onChange={event => setAgentQuery(event.target.value)} placeholder="e.g. Recruiter jobs in India, Europe, and remote worldwide"/><button className="button button-primary" type="submit" disabled={agentBusy || health !== 'online'}>{agentBusy ? <><RefreshCw size={15} className="spin-icon"/> Running…</> : <><Bot size={16}/> Run job agent</>}</button></div><SearchFilters region={searchRegion} setRegion={setSearchRegion} customLocation={customLocation} setCustomLocation={setCustomLocation} selectedWorkModes={selectedWorkModes} setSelectedWorkModes={setSelectedWorkModes} selectedEmploymentTypes={selectedEmploymentTypes} setSelectedEmploymentTypes={setSelectedEmploymentTypes} compact/><div className="agent-command-options"><label className="agent-auto-apply-toggle"><input type="checkbox" checked={agentAutoApply} onChange={event => setAgentAutoApply(event.target.checked)}/><span><strong>Auto-fill and submit supported applications</strong><small>Requires AUTO_SUBMIT_ENABLED=true, a configured browser, supported sites, and complete verified answers.</small></span></label><span className="agent-coverage-note"><ShieldCheck size={14}/> Searches enabled sources; optional JobSpy must be installed and enabled</span></div></form>
      {agentError && <div className="inline-alert error-alert"><AlertCircle size={15}/>{agentError}</div>}
      {agentReport && <div className="agent-run-report"><strong>{agentReport.message || 'Agent run finished'}</strong>{agentReport.query && <span>Query: {agentReport.query}</span>}<span>Posting window: {getPostingWindow(agentReport.posting_window_key || '24h').label}</span><span>Location scope: {regionLabel(agentReport.region_key || searchRegion, agentReport.custom_location || customLocation)}</span><span>Work preferences: {[...(agentReport.work_modes || selectedWorkModes).map(key => WORK_MODE_OPTIONS.find(item => item.key === key)?.label || key), ...(agentReport.employment_types || selectedEmploymentTypes).map(key => EMPLOYMENT_TYPE_OPTIONS.find(item => item.key === key)?.label || key)].join(', ')}</span><div><span>{agentReport.sources_checked ?? 0} boards checked</span><span>{agentReport.discovered_fresh ?? 0} fresh jobs</span><span>{agentReport.applications_created ?? 0} app records created</span><span>{agentReport.submitted ?? 0} confirmed submissions</span></div>{(agentReport.warnings || []).length > 0 && <ul>{agentReport.warnings.slice(0, 3).map((warning, idx) => <li key={idx}>{warning}</li>)}</ul>}</div>}
    </section>

    <section className="metrics-grid">
      <MetricCard icon={BriefcaseBusiness} label="Jobs tracked" value={jobs.length} foot="Your saved opportunities" color="violet" trend={jobs.length ? 'up' : null}/>
      <MetricCard icon={Gauge} label="Profile completion" value={`${completion}%`} foot={completion === 100 ? 'You’re ready to match' : 'Add details to improve matches'} color="teal" progress={completion}/>
      <MetricCard icon={Zap} label="Keyword matching" value="Active" foot="Transparent baseline scoring" color="amber" badge="PHASE 4"/>
      <MetricCard icon={ShieldCheck} label="Application workflow" value="Review first" foot="Auto-submit is opt-in and off by default" color="blue"/>
    </section>

    <section className="dashboard-grid">
      <div className="content-panel recent-panel"><div className="panel-topline"><div><span className="section-overline">YOUR PIPELINE</span><h2>Recently tracked jobs</h2><p>Keep interesting opportunities within reach.</p></div><button className="subtle-link" onClick={() => navigate('jobs')}>View all <ArrowRight size={15}/></button></div>
        {recentJobs.length ? <div className="job-list-mini">{recentJobs.map(job => <JobRow key={job.id} job={job} />)}</div> : <EmptyJobs onAdd={() => navigate('jobs')}/>}
      </div>
      <div className="content-panel profile-strength-panel"><div className="panel-topline"><div><span className="section-overline">YOUR FOUNDATION</span><h2>Profile strength</h2></div><div className="round-icon violet-round"><UserRound size={18}/></div></div><div className="strength-score"><div><strong>{completion}<small>%</small></strong><span>{completion === 100 ? 'Looking good!' : completion >= 60 ? 'Great progress' : 'Let’s get started'}</span></div><div className="strength-ring" style={{'--progress': `${completion * 3.6}deg`}}><div>{completion}%</div></div></div><div className="strength-track"><div style={{width: `${completion}%`}}/></div><p className="strength-note">A complete profile helps future matching and screening drafts stay relevant to your experience.</p><button className="button button-outline full-width" onClick={() => navigate('profile')}>{completion === 100 ? 'Edit profile' : 'Finish your profile'}<ArrowRight size={15}/></button><div className="privacy-note"><LockKeyhole size={14}/><span>Your profile stays local in this version.</span></div></div>
    </section>

    <section className="next-steps-section"><div className="next-section-heading"><div><span className="section-overline">YOUR WORKFLOW</span><h2>A little progress goes a long way.</h2></div><span className="roadmap-note">THE JOURNEY</span></div><div className="workflow-grid"><WorkflowCard number="01" icon={UserRound} title="Set up your profile" desc="Add your background, skills, and job preferences." status={completion === 100 ? 'Complete' : 'Start here'} state={completion === 100 ? 'done' : 'current'} onClick={() => navigate('profile')}/><WorkflowCard number="02" icon={Compass} title="Build your shortlist" desc="Save roles and keep useful job links together." status={jobs.length ? `${jobs.length} saved` : 'Ready when you are'} state={jobs.length ? 'done' : 'next'} onClick={() => navigate('jobs')}/><WorkflowCard number="03" icon={WandSparkles} title="Match & prepare" desc="Keyword-based fit scores are now shown on saved jobs; stronger AI matching comes later." status="Baseline active" state="current" onClick={() => navigate('jobs')}/></div></section>
  </>;
}

function MetricCard({ icon: Icon, label, value, foot, color, progress, badge, trend }) {
  return <div className={`metric-card metric-${color}`}><div className="metric-top"><div className="metric-icon"><Icon size={18}/></div>{badge ? <span className="metric-badge">{badge}</span> : trend ? <ArrowUpRight size={15} className="metric-arrow"/> : null}</div><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-foot">{progress !== undefined && <span className="tiny-progress"><span style={{width: `${progress}%`}}/></span>}{foot}</div></div>;
}

function JobRow({ job }) {
  const methodLabel = job.match_method === 'hybrid_semantic' ? 'hybrid semantic match' : 'rule-based baseline';
  return <article className="job-row"><div className="company-logo-placeholder">{String(job.company || '?').slice(0, 1).toUpperCase()}</div><div className="job-row-main"><strong>{job.title}</strong><span>{job.company} <i>·</i> {job.location || 'Location not specified'}</span><div className="job-row-meta"><span className="job-work-mode">{job.work_mode || 'Work mode unknown'}</span><span className="posted-label"><Clock3 size={12}/>{job.age_hours !== undefined && job.age_hours !== null ? (job.age_hours < 1 ? `${Math.max(1, Math.round(job.age_hours * 60))}m ago` : `${job.age_hours.toFixed(1)}h ago`) : formatPosted(job.posted_at)}</span>{job.verified_posting_time && <span className="verified-label"><CheckCircle2 size={12}/> Time verified</span>}{job.match_score !== undefined && <span className="match-score-pill" title={`${job.matching_note || methodLabel}. ${job.match_reasons?.join(' ') || ''}`}>{job.match_score}% {methodLabel}</span>}{job.provider && <span className="source-chip">{job.provider}</span>}{job.already_saved && <span className="source-chip saved-chip">Already saved</span>}</div></div><a className="external-job-link" href={job.source_url} target="_blank" rel="noreferrer" aria-label={`Open ${job.title} at ${job.company}`}><ExternalLink size={16}/></a></article>;
}

function ResearchReport({ jobs, title = 'Ranked qualifying jobs', unverified = false, postingWindowLabel = 'the selected window', onAnalyzeJob, onPrepareApplication, applicationBusyId }) {
  const [analyses, setAnalyses] = useState({});
  const [analysisBusyId, setAnalysisBusyId] = useState(null);
  const [analysisErrors, setAnalysisErrors] = useState({});
  const ranked = [...(jobs || [])].sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
  async function handleAnalyze(job) {
    setAnalysisErrors(previous => ({ ...previous, [job.id]: '' }));
    setAnalysisBusyId(job.id);
    try {
      const data = await onAnalyzeJob(job);
      setAnalyses(previous => ({ ...previous, [job.id]: data }));
    } catch (error) {
      setAnalysisErrors(previous => ({ ...previous, [job.id]: error.message || 'Could not analyze this job.' }));
    } finally {
      setAnalysisBusyId(null);
    }
  }
  async function handlePrepare(job) {
    try {
      await onPrepareApplication(job, analyses[job.id] || null);
    } catch (error) {
      setAnalysisErrors(previous => ({ ...previous, [job.id]: error.message || 'Could not prepare this application.' }));
    }
  }
  if (!ranked.length) return null;
  const isRemoteRole = job => /remote|work from home|\bwfh\b|worldwide|anywhere/i.test(`${job.work_mode || ''} ${job.location || ''}`);
  const isIndiaLocation = job => /\b(india|delhi|gurugram|gurgaon|noida|mumbai|bengaluru|bangalore|hyderabad|pune|chennai|kolkata|jaipur|ahmedabad|kochi|indore|bhopal)\b/i.test(job.location || '');
  const isDelhiNcrRole = job => /\b(delhi|gurugram|gurgaon|noida|ncr)\b/i.test(job.location || '');
  const isListedOutsideIndia = job => /\b(united states|usa|u\.s\.|united kingdom|uk|canada|australia|singapore|germany|france|netherlands|uae|united arab emirates|dubai|saudi arabia|qatar|japan|south korea|europe|africa|brazil|new zealand)\b/i.test(job.location || '') && !isIndiaLocation(job);
  const postedLabel = job => {
    if (job.age_hours !== undefined && job.age_hours !== null) {
      return job.age_hours < 1 ? `${Math.max(1, Math.round(job.age_hours * 60))} minutes ago` : `${job.age_hours.toFixed(1)} hours ago`;
    }
    return job.posted_at ? formatPosted(job.posted_at) : 'Not verified';
  };
  return <div className="research-report">
    <div className="research-report-intro"><div><span className="section-overline">RESEARCH REPORT</span><h3>{title} <span>{ranked.length}</span></h3><p>{unverified ? 'These candidates do not yet have a trustworthy original posting-time signal. Open the source and verify before applying.' : `Sorted by the app's explainable profile-fit estimate. Posting-time evidence is checked separately against ${postingWindowLabel}.`}</p></div><span className="research-score-note">Estimated profile fit · not employer scoring</span></div>
    <div className="research-table-wrap"><table className="research-table"><thead><tr><th>Rank</th><th>Job title</th><th>Company</th><th>Location / work mode</th><th>Posted time</th><th>Experience required</th><th>Salary</th><th>Match score</th><th>Direct link</th></tr></thead><tbody>
      {ranked.map((job, index) => <tr key={job.id || job.source_url || `${job.title}-${index}`}>
        <td>{index + 1}</td>
        <td><strong>{job.title}</strong><small>{job.source_company || job.provider || 'Job source'}</small></td>
        <td>{job.company}</td>
        <td>{job.location || 'Not specified'}<small>{job.work_mode || 'Work mode unknown'}</small></td>
        <td><span className={`research-time ${job.verified_posting_time && !unverified ? 'verified' : 'unverified'}`}>{postedLabel(job)}</span></td>
        <td>{job.experience_required || 'Not disclosed'}</td>
        <td>{job.salary_range || 'Not disclosed'}</td>
        <td><span className="research-match-score">{job.match_score ?? 0}/100</span><small className="research-score-method">{job.match_method === 'hybrid_semantic' ? `Hybrid · cosine ${Number(job.semantic_similarity || 0).toFixed(2)}` : 'Rule-based baseline'}</small></td>
        <td><a className="research-apply-link" href={job.source_url} target="_blank" rel="noreferrer">Open listing <ExternalLink size={12}/></a></td>
      </tr>)}
    </tbody></table></div>
    <div className="research-details-list"><h4>Detailed job verification & profile match breakdown</h4>
      {ranked.map((job, index) => <details className="research-detail" key={`${job.source_url}-details`}>
        <summary><span>{index + 1}. {job.title} — {job.company}</span><span className="research-summary-score">{job.match_score ?? 0}/100</span></summary>
        <div className="research-detail-body">
          <div><strong>Why your profile matches</strong><ul>{(job.match_reasons?.length ? job.match_reasons : ['No profile-match explanation was available for this listing.']).map((item, i) => <li key={i}>{item}</li>)}</ul><p className="research-score-note">{job.matching_note || (job.match_method === 'hybrid_semantic' ? 'Hybrid score combines rule evidence with local embedding similarity.' : 'Rule-based estimate; semantic matching was not available for this result.')}</p></div>
          {job.score_breakdown && Object.keys(job.score_breakdown).length > 0 && <div><strong>Score breakdown</strong><div className="score-breakdown-grid">{Object.entries(job.score_breakdown).filter(([key, value]) => key !== 'semantic_alignment' && value && typeof value === 'object' && 'score' in value).map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ')}</span><b>{value.score}/{value.max}</b></div>)}</div></div>}
          <div><strong>Most important skills found in the listing</strong><p>{job.required_skills?.length ? job.required_skills.join(', ') : 'The job page did not expose a clear skills list.'}</p></div>
          <div><strong>Posting-time verification</strong><p>{job.posting_time_evidence || (job.verified_posting_time ? 'A publication timestamp was supplied by the source.' : 'Original publication time not verified from the page.')}</p></div>
          {job.description && <div><strong>Listing summary / captured description</strong><p>{String(job.description).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').slice(0, 900)}{job.description.length > 900 ? '…' : ''}</p></div>}
          <div><strong>Concerns to review</strong>{job.concerns?.length ? <ul>{job.concerns.map((item, i) => <li key={i}>{item}</li>)}</ul> : <p>No additional concerns detected by the basic rule-based checks. Review the original posting yourself.</p>}</div>
          <div className="research-source-origin"><strong>Discovered through</strong><p>{job.source_company || job.provider || 'Source not reported'}</p></div>
          <div className="research-original-url"><strong>Original job-posting URL</strong><a href={job.source_url} target="_blank" rel="noreferrer">{job.source_url}</a></div>
          <div className="research-job-action-row">
            <button className="button button-secondary small-button" disabled={!job.id || analysisBusyId === job.id} onClick={() => handleAnalyze(job)} title={!job.id ? 'Save this listing before analyzing it' : 'Analyze the saved job against your profile and resume'}>
              <WandSparkles size={13}/>{analysisBusyId === job.id ? 'Analyzing…' : analyses[job.id] ? 'Refresh AI analysis' : 'Analyze against my resume'}
            </button>
            <button className="button button-primary small-button" disabled={!job.id || applicationBusyId === job.id} onClick={() => handlePrepare(job)} title={!job.id ? 'Save this listing before preparing an application' : 'Create an application record and draft screening answers; does not submit'}>
              <FileCheck2 size={13}/>{applicationBusyId === job.id ? 'Preparing…' : 'Prepare application'}
            </button>
          </div>
          {analysisErrors[job.id] && <div className="inline-alert error-alert research-analysis-error"><AlertCircle size={14}/>{analysisErrors[job.id]}</div>}
          {analyses[job.id] && <section className="job-ai-analysis">
            <div className="job-ai-analysis-heading"><div><span className="section-overline">PROFILE ANALYSIS</span><h5>How this role fits your resume</h5></div><span className={`analysis-provider-pill ${analyses[job.id].ai_assisted ? 'ai-active' : ''}`}>{analyses[job.id].analysis_provider}{analyses[job.id].ai_assisted ? ' · AI assisted' : ' · rules fallback'}</span></div>
            <p className="job-ai-fit-summary">{analyses[job.id].fit_summary}</p>
            <div className="analysis-score-method"><strong>Match score: {analyses[job.id].match_score}/100</strong><span>{analyses[job.id].match_method === 'hybrid_semantic' ? `Hybrid semantic + evidence · rule baseline ${analyses[job.id].rule_based_score}/100 · embedding cosine ${Number(analyses[job.id].semantic_similarity || 0).toFixed(2)}` : 'Rule-based score; local semantic embeddings were not available for this analysis.'}</span>{analyses[job.id].matching_note && <small>{analyses[job.id].matching_note}</small>}</div>
            {analyses[job.id].score_breakdown && <div className="score-breakdown-grid analysis-breakdown">{Object.entries(analyses[job.id].score_breakdown).filter(([key, value]) => key !== 'semantic_alignment' && value && typeof value === 'object' && 'score' in value).map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ')}</span><b>{value.score}/{value.max}</b></div>)}</div>}
            <div className="job-ai-analysis-grid">
              <div><strong>Experience fit</strong><p>{analyses[job.id].experience_assessment}</p></div>
              <div><strong>Location fit</strong><p>{analyses[job.id].location_assessment}</p></div>
              <div><strong>Skills evidenced in your profile</strong>{analyses[job.id].skills_evidenced_by_profile?.length ? <div className="analysis-chip-list">{analyses[job.id].skills_evidenced_by_profile.map(skill => <span key={skill}>{skill}</span>)}</div> : <p>No required skill was confidently found in the saved profile text.</p>}</div>
              <div><strong>Skills to confirm</strong>{analyses[job.id].skills_not_found_in_profile?.length ? <div className="analysis-chip-list warning-chips">{analyses[job.id].skills_not_found_in_profile.map(skill => <span key={skill}>{skill}</span>)}</div> : <p>No obvious skill gaps found by the keyword check; review the full description.</p>}</div>
              <div><strong>Resume points to emphasize</strong><ul>{(analyses[job.id].resume_points_to_emphasize || []).map((item, i) => <li key={i}>{item}</li>)}</ul></div>
              <div><strong>Suggested screening questions</strong><ol>{(analyses[job.id].suggested_screening_questions || []).map((item, i) => <li key={i}>{item}</li>)}</ol></div>
            </div>
            {analyses[job.id].concerns?.length > 0 && <div className="job-ai-concerns"><strong>Potential concerns</strong><ul>{analyses[job.id].concerns.map((item, i) => <li key={i}>{item}</li>)}</ul></div>}
            <small className="job-ai-verification-note">{analyses[job.id].verification_note}</small>
          </section>}
        </div>
      </details>)}
    </div>
    {!unverified && <div className="research-final-summary">
      <div className="research-summary-heading"><div><span className="section-overline">FINAL SUMMARY</span><h4>Search snapshot</h4><p>Counts describe the current result set only; location categories are inferred from listing text.</p></div><span className="research-summary-total">{ranked.length} verified jobs</span></div>
      <div className="research-summary-metrics">
        <div><strong>{ranked.filter(isRemoteRole).length}</strong><span>Remote / WFH</span></div>
        <div><strong>{ranked.filter(isDelhiNcrRole).length}</strong><span>Delhi NCR locations</span></div>
        <div><strong>{ranked.filter(isListedOutsideIndia).length}</strong><span>Locations listed outside India</span></div>
      </div>
      <div className="research-top-matches"><strong>Strongest matches by estimated profile fit</strong><ol>{ranked.slice(0, 5).map((job, i) => <li key={`top-${job.source_url}`}><a href={job.source_url} target="_blank" rel="noreferrer">{job.title} — {job.company}</a><span>{job.match_score ?? 0}/100</span></li>)}</ol></div>
    </div>}
  </div>;
}

function EmptyJobs({ onAdd }) {
  return <div className="empty-state"><div className="empty-illustration"><div className="empty-orbit empty-orbit-a"/><div className="empty-orbit empty-orbit-b"/><div className="empty-file"><FileText size={25}/><span><i/><i/><i/></span></div><div className="empty-star empty-star-a">✦</div><div className="empty-star empty-star-b">✧</div></div><h3>Your next opportunity starts here.</h3><p>No jobs in your saved list yet. Run a fresh search above or add a role you found elsewhere.</p><button className="button button-primary" onClick={onAdd}><Plus size={16}/> Add manually</button><span className="empty-footnote"><Sparkles size={12}/> Fresh, timestamp-verified discoveries are saved automatically.</span></div>;
}

function WorkflowCard({ number, icon: Icon, title, desc, status, state, onClick }) {
  return <button className={`workflow-card workflow-${state}`} onClick={onClick}><div className="workflow-card-top"><span className="workflow-number">{number}</span><span className="workflow-icon"><Icon size={19}/></span></div><h3>{title}</h3><p>{desc}</p><div className="workflow-card-bottom"><span className={`workflow-status ${state}`}>{state === 'done' && <Check size={12}/>} {status}</span><ArrowUpRight size={15} className="workflow-arrow"/></div></button>;
}

function JobsView({ jobs, query, setQuery, openAdd, jobMessage, sources, sourceDraft, setSourceDraft, sourceMessage, sourceBusy, addSource, removeSource, toggleSource, discoveryQuery, setDiscoveryQuery, discoveryBusy, discoveryError, discoveryResult, includeUnverified, setIncludeUnverified, runDiscovery, postingWindow, setPostingWindow, searchRegion, setSearchRegion, customLocation, setCustomLocation, selectedWorkModes, setSelectedWorkModes, selectedEmploymentTypes, setSelectedEmploymentTypes, onAnalyzeJob, onPrepareApplication, onManualApply, onAutoApply, applicationBusyId, profile, navigate, uploadResume, resumeUploading, resumeMessage, autoSubmitEnabled, applicationActionMessage, selectedQueueJobs, onToggleQueueJob, onSelectAllQueueJobs, onClearQueueJobs, queueSelectedApplications, queueBusy, queueMessage }) {
  const freshJobs = discoveryResult?.fresh_jobs || [];
  const unverifiedJobs = discoveryResult?.unverified_jobs || [];
  const [sourceDetailsOpen, setSourceDetailsOpen] = useState(false);
  const [savedDetailsOpen, setSavedDetailsOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const emptyResultReason = !discoveryResult ? ''
    : (discoveryResult.raw_postings_count ?? 0) === 0
      ? 'Enabled sources returned no postings. Open source diagnostics below to see which connectors need attention.'
      : (discoveryResult.query_matched_count ?? 0) === 0
        ? `${discoveryResult.raw_postings_count} postings were fetched, but none matched these role terms. Try shorter keywords such as Recruiter, HR, or Talent Acquisition.`
        : (discoveryResult.timestamp_unverified_candidates_count ?? 0) > 0 && !includeUnverified
          ? `${discoveryResult.timestamp_unverified_candidates_count} matching listings have unknown or unverified posting dates. Turn on the option above to inspect those leads.`
          : (discoveryResult.time_window_excluded_count ?? 0) > 0
            ? `${discoveryResult.time_window_excluded_count} matching postings fell outside this date window. Try Past 7 days or Past 1 month.`
            : 'No listing qualified for these filters. Broaden the location, work type, or posting window.';

  async function handleResumeUpload(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    const uploaded = await uploadResume(file);
    if (uploaded && discoveryResult) await runDiscovery();
  }

  const activeSourceCount = sources.filter(source => source.enabled).length;
  const postingWindowLabel = getPostingWindow(discoveryResult?.posting_window_key || postingWindow).label.toLowerCase();

  return <div className="view-stack simple-job-hunt">
    <section className="simple-flow-hero">
      <div className="simple-flow-icon"><Sparkles size={22}/></div>
      <div className="simple-flow-copy"><span className="section-overline">YOUR JOB HUNT</span><h2>Find jobs. Match your CV. Apply.</h2><p>Search enabled sources once, see how closely each role matches your resume, then choose manual or supported automatic application.</p></div>
      <div className={`simple-flow-status ${profile.resume_original_filename ? 'ready' : 'needs-resume'}`}><span/>{profile.resume_original_filename ? 'CV attached' : 'CV needed for best matches'}</div>
    </section>

    <section className="content-panel simple-search-panel">
      <div className="simple-step-heading"><span className="simple-step-number">01</span><div><h2>Find jobs</h2><p>Search across your enabled public feeds and configured company boards.</p></div></div>
      <form className="simple-discovery-form" onSubmit={runDiscovery}>
        <label className="simple-query-field"><span>Job titles or keywords</span><input value={discoveryQuery} onChange={event => setDiscoveryQuery(event.target.value)} maxLength={2000} placeholder="IT Recruiter, Talent Acquisition Specialist, HR Executive…"/></label>
        <label className="simple-window-field"><span>Posted within</span><select aria-label="Job search posting window" value={postingWindow} onChange={event => setPostingWindow(event.target.value)}>{POSTING_WINDOWS.map(option => <option key={option.key} value={option.key}>{option.label}</option>)}</select></label>
        <button className="button button-primary simple-search-button" type="submit" disabled={discoveryBusy || activeSourceCount === 0}>{discoveryBusy ? <><RefreshCw size={15} className="spin-icon"/> Searching…</> : <><Search size={16}/> Find matching jobs</>}</button>
      </form>
      <div className="simple-search-secondary-row">
        <button type="button" className="simple-filter-toggle" onClick={() => setFiltersOpen(value => !value)}><Globe2 size={15}/>{filtersOpen ? 'Hide location & work filters' : 'Location & work filters'}<span>{regionLabel(searchRegion, customLocation)} · {selectedWorkModes.length} work modes</span><ChevronDown size={14} className={filtersOpen ? 'rotate-chevron' : ''}/></button>
        <label className="simple-unverified-toggle"><input type="checkbox" checked={includeUnverified} onChange={event => setIncludeUnverified(event.target.checked)}/> Also show relevant leads with unverified posting dates (recommended)</label>
      </div>
      {filtersOpen && <div className="simple-filters-expanded"><SearchFilters region={searchRegion} setRegion={setSearchRegion} customLocation={customLocation} setCustomLocation={setCustomLocation} selectedWorkModes={selectedWorkModes} setSelectedWorkModes={setSelectedWorkModes} selectedEmploymentTypes={selectedEmploymentTypes} setSelectedEmploymentTypes={setSelectedEmploymentTypes}/></div>}
      {activeSourceCount === 0 && <div className="inline-alert discovery-alert"><AlertCircle size={16}/><span>No active job sources.</span><button type="button" className="button button-secondary small-button" onClick={() => { setSourceDetailsOpen(true); document.getElementById('simple-source-manager')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}>Set up sources</button></div>}
      {discoveryError && <div className="inline-alert error-alert"><AlertCircle size={16}/>{discoveryError}</div>}
      {applicationActionMessage && <div className={`inline-alert ${/could not|failed|error/i.test(applicationActionMessage) ? 'error-alert' : 'success-alert'}`}><AlertCircle size={15}/><span>{applicationActionMessage}</span></div>}
      {jobMessage && <div className="inline-alert"><CheckCircle2 size={15}/><span>{jobMessage}</span></div>}
    </section>

    <section className="content-panel simple-resume-panel">
      <div className="simple-step-heading"><span className="simple-step-number">02</span><div><h2>Attach your resume</h2><p>We'll use this CV and your saved profile to calculate a role-fit score.</p></div></div>
      <div className={`simple-resume-status-card ${profile.resume_original_filename ? 'resume-ready' : 'resume-missing'}`}>
        <div className="simple-resume-file-icon"><FileText size={21}/></div>
        <div className="simple-resume-file-info">
          {profile.resume_original_filename ? <><strong>{profile.resume_original_filename}</strong><span>{profile.resume_size_bytes ? `${(profile.resume_size_bytes / 1024).toFixed(0)} KB` : 'Resume attached'}{profile.resume_uploaded_at ? ` · Updated ${new Date(profile.resume_uploaded_at).toLocaleDateString()}` : ''} · Used for matching and application preparation</span></> : <><strong>No resume attached yet</strong><span>Upload PDF, DOC, DOCX or RTF up to 2 MB. Your file is stored locally.</span></>}
        </div>
        <label className="button button-secondary simple-upload-button"><input type="file" accept=".pdf,.doc,.docx,.rtf,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/rtf" onChange={handleResumeUpload} disabled={resumeUploading}/>{resumeUploading ? <><RefreshCw size={14} className="spin-icon"/> Uploading…</> : <><FileText size={14}/>{profile.resume_original_filename ? 'Replace CV' : 'Attach CV'}</>}</label>
        <button type="button" className="simple-profile-link" onClick={() => navigate('profile')}>Profile details <ArrowRight size={13}/></button>
      </div>
      {resumeMessage && <div className={`inline-alert ${/could not|must be|error/i.test(resumeMessage) ? 'error-alert' : 'success-alert'}`}><AlertCircle size={15}/><span>{resumeMessage}</span></div>}
      {!profile.resume_original_filename && <p className="simple-resume-hint"><ShieldCheck size={13}/> You can search without a CV, but match scores will be based on saved profile details only until you attach one.</p>}
    </section>

    {discoveryResult && <section className="simple-results-section">
      <div className="simple-step-heading simple-results-heading"><span className="simple-step-number">03</span><div><h2>Jobs to review <span className="simple-result-count">{freshJobs.length + unverifiedJobs.length}</span></h2><p>{freshJobs.length} verified within {postingWindowLabel}; {unverifiedJobs.length} more have unverified posting dates. Review both groups before applying.</p></div><span className="simple-last-checked">Checked {new Date(discoveryResult.checked_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span></div>
      <div className="simple-result-stats"><div><strong>{discoveryResult.raw_postings_count ?? 0}</strong><span>postings fetched</span></div><div><strong>{discoveryResult.sources_checked ?? 0}</strong><span>sources checked</span></div><div><strong>{discoveryResult.query_matched_count ?? 0}</strong><span>matched keywords</span></div><div><strong>{discoveryResult.timestamp_unverified_candidates_count ?? 0}</strong><span>unverified-date leads</span></div></div>
      {(freshJobs.length + unverifiedJobs.length) > 0 && <div className="application-queue-toolbar"><div className="application-queue-copy"><span className="queue-kicker">APPLICATION QUEUE</span><strong>{selectedQueueJobs.length} selected <span>/ 50</span></strong><p>Select vacancies from either results section, then prepare review drafts in one batch. This never submits applications.</p></div><div className="application-queue-actions"><button type="button" className="button button-secondary small-button" onClick={() => onSelectAllQueueJobs([...freshJobs, ...(includeUnverified ? unverifiedJobs : [])])}>Select visible jobs</button><button type="button" className="button button-quiet small-button" onClick={onClearQueueJobs} disabled={!selectedQueueJobs.length || queueBusy}>Clear</button><button type="button" className="button button-primary small-button" onClick={queueSelectedApplications} disabled={!selectedQueueJobs.length || queueBusy}>{queueBusy ? <><RefreshCw size={13} className="spin-icon"/> Preparing…</> : <><ListChecks size={14}/> Prepare selected ({selectedQueueJobs.length})</>}</button></div>{queueMessage && <div className={`queue-feedback ${/could not|failed|error/i.test(queueMessage) ? 'error' : ''}`}>{queueMessage}</div>}</div>}
      <div className="simple-subsection-title"><h3>Verified fresh matches <span>{freshJobs.length}</span></h3><p>These listings have source evidence placing them inside the selected posting window.</p></div>
      {freshJobs.length ? <SimpleJobResults jobs={freshJobs} title="Best verified matches" profileHasResume={Boolean(profile.resume_original_filename)} autoSubmitEnabled={autoSubmitEnabled} applicationBusyId={applicationBusyId} onAnalyzeJob={onAnalyzeJob} onManualApply={onManualApply} onAutoApply={onAutoApply} selectedJobs={selectedQueueJobs} onToggleQueueJob={onToggleQueueJob} unverified={false}/> : <div className="content-panel discovery-empty"><div className="empty-mini-icon"><Search size={20}/></div><strong>No verified matches in this search.</strong><p>{emptyResultReason}</p></div>}
      {includeUnverified && <div className="simple-unverified-section"><div className="simple-subsection-title"><h3>More leads to review — posting date unverified <span>{unverifiedJobs.length}</span></h3><p>These are relevant to your selected role/location/work filters, but the source did not provide a trustworthy original posting timestamp. You can still open the job and apply manually after verifying it yourself; these are not counted as confirmed fresh jobs.</p></div>{unverifiedJobs.length ? <SimpleJobResults jobs={unverifiedJobs} title="Unverified leads" profileHasResume={Boolean(profile.resume_original_filename)} autoSubmitEnabled={autoSubmitEnabled} applicationBusyId={applicationBusyId} onAnalyzeJob={onAnalyzeJob} onManualApply={onManualApply} onAutoApply={onAutoApply} selectedJobs={selectedQueueJobs} onToggleQueueJob={onToggleQueueJob} unverified/> : <div className="discovery-empty compact-empty">No matching unverified listings were returned.</div>}</div>}
      <details className="simple-advanced-details"><summary>Source diagnostics <span>{discoveryResult.sources_checked ?? 0} checked</span></summary><div className="simple-source-diagnostics"><div className="discovery-summary discovery-summary-detailed"><div><strong>{discoveryResult.raw_postings_count ?? 0}</strong><span>raw postings fetched</span></div><div><strong>{discoveryResult.unique_postings_count ?? discoveryResult.raw_postings_count ?? 0}</strong><span>unique listings</span></div><div><strong>{discoveryResult.duplicate_removed_count ?? 0}</strong><span>duplicates removed</span></div><div><strong>{discoveryResult.query_matched_count ?? 0}</strong><span>matched job roles</span></div><div><strong>{discoveryResult.timestamp_unverified_candidates_count ?? 0}</strong><span>unverified dates</span></div><div><strong>{discoveryResult.time_window_excluded_count ?? 0}</strong><span>outside date window</span></div></div>
        {Array.isArray(discoveryResult.filter_funnel) && discoveryResult.filter_funnel.length > 0 && <div className="filter-funnel-panel"><div className="filter-funnel-heading"><strong>Search funnel</strong><span>Why raw postings become final results</span></div>{discoveryResult.filter_funnel.map((stage, index) => <div className="filter-funnel-row" key={`${stage.stage}-${index}`}><div className="filter-funnel-stage"><strong>{stage.stage}</strong><small>{stage.description}</small></div><div className="filter-funnel-numbers"><span><b>{stage.input_count}</b><small>input</small></span><span><b>{stage.passed_count}</b><small>passed</small></span><span><b>{stage.excluded_count}</b><small>removed</small></span></div></div>)}</div>}
        <div className="source-status-list source-status-list-visible"><strong>Source status</strong>{(discoveryResult.source_statuses || []).map(status => <div key={status.source_id} className="source-status-row"><span className={`source-status-dot ${status.status}`}/><span>{status.company_name}</span><small>{status.status === 'success' ? `${status.fetched_count} postings fetched` : status.message}</small></div>)}</div>
        {discoveryResult.exclusion_reason_counts && Object.keys(discoveryResult.exclusion_reason_counts).length > 0 && <details className="excluded-postings-details"><summary>Why listings were excluded or separated <span>{discoveryResult.excluded_listing_count ?? 0} records</span></summary><div className="exclusion-reason-chips">{Object.entries(discoveryResult.exclusion_reason_counts).sort((a,b) => b[1]-a[1]).map(([reason,count]) => <span key={reason}><b>{count}</b> {reason.replaceAll('_',' ')}</span>)}</div>{discoveryResult.excluded_listings?.length > 0 && <div className="excluded-posting-list">{discoveryResult.excluded_listings.slice(0, 100).map((item, index) => <article className="excluded-posting-row" key={`${item.source_url}-${item.reason_code}-${index}`}><div><strong>{item.title}</strong><span>{item.company} · {item.location} · {item.provider}</span><p>{item.reason}</p><small>{item.posting_time_evidence}</small></div>{item.source_url && <a href={item.source_url} target="_blank" rel="noopener noreferrer">Open source <ExternalLink size={12}/></a>}</article>)}</div>}{(discoveryResult.excluded_listings_truncated || (discoveryResult.excluded_listings?.length ?? 0) > 100) && <p className="excluded-truncated-note">Showing the first 100 exclusion examples. Summary counts cover all records; {discoveryResult.excluded_listings_truncated ? 'the API also capped the detailed sample list' : 'all returned reasons are available by expanding the sample further in a future version'}.</p>}</details>}
        {discoveryResult.web_search_notes?.length > 0 && <div className="inline-alert"><AlertCircle size={15}/><div>{discoveryResult.web_search_notes.map((note, i) => <p key={i}>{note}</p>)}</div></div>}{!discoveryResult.web_search_configured && <div className="source-note"><Globe2 size={15}/><span>For broad web research, configure <code>BRAVE_SEARCH_API_KEY</code> in <code>backend/.env</code> and restart. Search-index results are not considered timestamp-verified without original-page evidence.</span></div>}</div></details>
      <details className="simple-advanced-details"><summary>Detailed research report <span>Full verification and score breakdown</span></summary><ResearchReport jobs={freshJobs} postingWindowLabel={postingWindowLabel} onAnalyzeJob={onAnalyzeJob} onPrepareApplication={onPrepareApplication} applicationBusyId={applicationBusyId}/></details>
    </section>}

    <details id="simple-source-manager" open={sourceDetailsOpen} onToggle={event => setSourceDetailsOpen(event.currentTarget.open)} className="content-panel simple-advanced-details simple-source-manager">
      <summary>Manage sources <span>{activeSourceCount} active of {sources.length}</span></summary>
      <div className="source-manager-panel simple-source-manager-inner">
        <div className="discovery-panel-heading"><div><span className="section-overline">ADVANCED SETUP</span><h2>Job sources</h2><p>Connect public ATS boards, aggregators, optional web research, or the paused-by-default JobSpy multi-portal connector. To opt into JobSpy, install backend/requirements-jobspy.txt, set JOBSPY_ENABLED=true, restart the backend, and enable the source. Use it only where each portal's terms permit; it does not bypass access controls.</p></div><div className="source-heading-icon"><Database size={18}/></div></div>
        <div className="source-help-grid"><div><strong>Greenhouse / Lever</strong><p>For <code>boards.greenhouse.io/acme</code> or <code>jobs.lever.co/acme</code>, enter <code>acme</code>.</p></div><div><strong>Arbeitnow / Remote OK / Jobicy / Himalayas</strong><p>Enter <code>default</code>. Public feeds provide additional international and remote leads. For Himalayas, retain visible source attribution and its supplied application link.</p></div><div><strong>Adzuna</strong><p>Enter a supported country code such as <code>in</code>, <code>gb</code>, or <code>us</code>. Configure API credentials in <code>backend/.env</code>.</p></div><div className="web-research-help"><strong>Brave Web Research</strong><p>Requires <code>BRAVE_SEARCH_API_KEY</code> in <code>backend/.env</code>. Usage may incur API charges.</p></div></div>
        <form className="source-add-form" onSubmit={addSource}><label><span>Provider</span><select value={sourceDraft.provider} onChange={event => setSourceDraft({...sourceDraft, provider: event.target.value, board_id: ['arbeitnow', 'remoteok', 'jobicy', 'himalayas', 'brave', 'jobspy'].includes(event.target.value) ? 'default' : event.target.value === 'adzuna' ? 'in' : ''})}><option value="greenhouse">Greenhouse company board</option><option value="lever">Lever company board</option><option value="arbeitnow">Arbeitnow public feed</option><option value="remoteok">Remote OK</option><option value="jobicy">Jobicy</option><option value="himalayas">Himalayas Remote Jobs</option><option value="adzuna">Adzuna (country search)</option><option value="brave">Brave Web Research</option><option value="jobspy">JobSpy multi-portal scraper (optional / experimental)</option></select></label><label><span>Company / feed name</span><input required value={sourceDraft.company_name} onChange={event => setSourceDraft({...sourceDraft, company_name: event.target.value})} placeholder="Company or feed name"/></label><label><span>Board ID / site slug</span><input required value={sourceDraft.board_id} onChange={event => setSourceDraft({...sourceDraft, board_id: event.target.value})} pattern="[A-Za-z0-9_-]{1,100}" title="Use only letters, numbers, hyphens, and underscores" placeholder="e.g. acme or default"/></label><button className="button button-secondary" type="submit" disabled={sourceBusy}>{sourceBusy ? 'Adding…' : <><Plus size={15}/> Add source</>}</button></form>
        {sourceMessage && <div className={`inline-alert ${sourceMessage.startsWith('Could not') ? 'error-alert' : 'success-alert'}`}>{sourceMessage}</div>}
        {sources.length ? <div className="configured-sources"><div className="configured-sources-heading"><strong>Configured sources</strong><span>{activeSourceCount} active</span></div>{sources.map(source => <div className={`configured-source-row ${source.enabled ? '' : 'source-disabled'}`} key={source.id}><div className={`provider-mark provider-${source.provider}`}>{{greenhouse:'G',lever:'L',arbeitnow:'A',remoteok:'R',jobicy:'J',himalayas:'H',adzuna:'Z',brave:'B',jobspy:'JS'}[source.provider] || '?'}</div><div className="configured-source-name"><strong>{source.company_name}</strong><span>{source.provider} · {source.board_id}</span></div><span className={`source-state-pill ${source.enabled ? 'enabled' : 'disabled'}`}>{source.enabled ? 'Active' : 'Paused'}</span><button className="icon-button source-icon-action" onClick={() => toggleSource(source)} title={source.enabled ? 'Pause source' : 'Enable source'} aria-label={source.enabled ? 'Pause source' : 'Enable source'}>{source.enabled ? <ToggleRight size={18}/> : <ToggleLeft size={18}/>}</button><button className="icon-button source-icon-action remove-source" onClick={() => removeSource(source.id)} title="Remove source" aria-label="Remove source"><Trash2 size={15}/></button></div>)}</div> : <div className="sources-empty"><Database size={17}/><span>No sources configured yet. Add a feed or company board here.</span></div>}
      </div>
    </details>

    <details open={savedDetailsOpen} onToggle={event => setSavedDetailsOpen(event.currentTarget.open)} className="content-panel simple-advanced-details simple-saved-jobs"><summary>Saved jobs <span>{jobs.length} tracked</span></summary><div className="simple-saved-jobs-inner"><div className="toolbar-row saved-jobs-toolbar"><div className="toolbar-title"><h2>Your saved jobs <span>{jobs.length}</span></h2><p>Manually added and discovered opportunities.</p></div><div className="toolbar-controls"><label className="table-search"><Search size={15}/><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search saved jobs…"/><button onClick={() => setQuery('')} title="Clear search" aria-label="Clear search"><X size={13}/></button></label><button className="button button-secondary" onClick={openAdd}><Plus size={16}/> Add manually</button></div></div>{jobs.length ? <div className="content-panel full-job-list"><div className="job-list-heading"><span>POSITION</span><span>WORK MODE</span><span>POSTED</span><span>OPEN</span></div>{jobs.map(job => <JobRow key={job.id} job={job}/>)}</div> : <div className="jobs-empty-panel"><EmptyJobs onAdd={openAdd}/></div>}</div></details>
  </div>;
}

function SimpleJobResults({ jobs, title, profileHasResume, autoSubmitEnabled, applicationBusyId, onAnalyzeJob, onManualApply, onAutoApply, selectedJobs = [], onToggleQueueJob, unverified = false }) {
  const [expanded, setExpanded] = useState({});
  const [analyses, setAnalyses] = useState({});
  const [analysisBusyId, setAnalysisBusyId] = useState(null);
  const [errors, setErrors] = useState({});
  const ranked = [...(jobs || [])].sort((a, b) => (b.match_score ?? 0) - (a.match_score ?? 0));

  async function toggleAnalysis(job) {
    if (expanded[job.id]) {
      setExpanded(previous => ({ ...previous, [job.id]: false }));
      return;
    }
    setExpanded(previous => ({ ...previous, [job.id]: true }));
    if (!job.id || analyses[job.id]) return;
    setAnalysisBusyId(job.id);
    setErrors(previous => ({ ...previous, [job.id]: '' }));
    try {
      const analysis = await onAnalyzeJob(job);
      setAnalyses(previous => ({ ...previous, [job.id]: analysis }));
    } catch (error) {
      setErrors(previous => ({ ...previous, [job.id]: error.message || 'Could not analyze this role.' }));
    } finally {
      setAnalysisBusyId(null);
    }
  }

  if (!ranked.length) return null;
  return <div className="simple-job-card-list" aria-label={title}>
    {ranked.map((job, index) => {
      const score = Math.max(0, Math.min(100, Number(job.match_score ?? 0)));
      const analysis = analyses[job.id];
      const posted = job.age_hours !== undefined && job.age_hours !== null
        ? (job.age_hours < 1 ? `${Math.max(1, Math.round(job.age_hours * 60))}m ago` : `${job.age_hours.toFixed(1)}h ago`)
        : (job.posted_at ? formatPosted(job.posted_at) : 'Date unverified');
      const reasons = (job.match_reasons || []).slice(0, 2);
      return <article className="simple-job-card" key={job.id || job.source_url || `${job.title}-${index}`}>
        <div className="simple-job-card-main">
          <div className="simple-company-mark">{String(job.company || '?').trim().slice(0, 1).toUpperCase()}</div>
          <div className="simple-job-info">
            <div className="simple-job-eyebrow"><span className="simple-job-source">{job.source_company || job.provider || 'Job source'}</span>{job.verified_posting_time && !unverified ? <span className="simple-verified"><CheckCircle2 size={11}/> Posting time verified</span> : <span className="simple-unverified"><Clock3 size={11}/> Verify posting date</span>}</div>
            <h3>{job.title}</h3>
            <p className="simple-job-company">{job.company || 'Company not specified'}</p>
            <div className="simple-job-meta"><span><Globe2 size={12}/>{job.location || 'Location not specified'}</span><span><BriefcaseBusiness size={12}/>{job.work_mode || 'Work mode unknown'}</span><span><Clock3 size={12}/>{posted}</span></div>
            {(job.salary_range || job.experience_required) && <div className="simple-job-extra">{job.salary_range && <span>{job.salary_range}</span>}{job.experience_required && <span>{job.experience_required} experience</span>}</div>}
          </div>
          <div className="simple-job-score" aria-label={`Estimated profile fit ${score} percent`}><div className="simple-score-number">{score}<small>%</small></div><span>{profileHasResume ? 'CV match' : 'Profile fit'}</span><div className="simple-score-track"><i style={{ width: `${score}%` }}/></div><small className="simple-score-method">{job.match_method === 'hybrid_semantic' ? 'Semantic + skills' : profileHasResume ? 'Profile evidence' : 'Add CV for better match'}</small></div>
        </div>
        {reasons.length > 0 && <div className="simple-job-reasons">{reasons.map((reason, reasonIndex) => <span key={`${job.id}-reason-${reasonIndex}`}><Check size={12}/>{reason}</span>)}</div>}
        <div className="simple-job-actions">
          <label className="queue-select-job"><input type="checkbox" checked={selectedJobs.some(item => jobSelectionKey(item) === jobSelectionKey(job))} onChange={() => onToggleQueueJob?.(job)} disabled={!job.source_url}/><span>Select</span></label>
          <button className="button button-quiet small-button" type="button" disabled={!job.id || analysisBusyId === job.id} onClick={() => toggleAnalysis(job)}>{analysisBusyId === job.id ? <><RefreshCw size={13} className="spin-icon"/> Analyzing…</> : expanded[job.id] ? 'Hide fit details' : <><WandSparkles size={13}/> Why this match?</>}</button>
          <a className="button button-secondary small-button" href={job.source_url} target="_blank" rel="noopener noreferrer" onClick={event => { event.preventDefault(); onManualApply(job); }}><ExternalLink size={13}/> Apply manually</a>
          <button className="button button-primary small-button" type="button" disabled={!job.id || applicationBusyId === job.id} onClick={() => onAutoApply(job, analysis || null)} title={autoSubmitEnabled ? 'Start the supported browser application workflow. Required unknown answers will stop for review.' : 'Prepare a draft in Application History. Auto-submit is currently disabled.'}>{applicationBusyId === job.id ? <><RefreshCw size={13} className="spin-icon"/> Working…</> : <><Zap size={13}/> Auto-apply</>}</button>
        </div>
        {!autoSubmitEnabled && <p className="simple-auto-note"><ShieldCheck size={12}/> Auto-submit is off. Auto-apply will prepare the draft and take you to review; it will not submit.</p>}
        {errors[job.id] && <div className="inline-alert error-alert"><AlertCircle size={14}/>{errors[job.id]}</div>}
        {expanded[job.id] && <div className="simple-fit-details">
          {analysis ? <>
            <div className="simple-fit-summary"><strong>Why your CV fits</strong><p>{analysis.fit_summary}</p><span>{analysis.analysis_provider}{analysis.ai_assisted ? ' · AI assisted' : ' · rules fallback'}</span></div>
            <div className="simple-fit-grid"><div><strong>Experience</strong><p>{analysis.experience_assessment}</p></div><div><strong>Location & work mode</strong><p>{analysis.location_assessment}</p></div><div><strong>Skills found in your profile</strong><p>{analysis.skills_evidenced_by_profile?.join(', ') || 'No clear skill evidence was found in saved profile text.'}</p></div><div><strong>Skills to confirm</strong><p>{analysis.skills_not_found_in_profile?.join(', ') || 'No obvious missing skill evidence detected.'}</p></div></div>
            {analysis.concerns?.length > 0 && <div className="simple-fit-concerns"><strong>Review these concerns</strong><ul>{analysis.concerns.map((concern, i) => <li key={i}>{concern}</li>)}</ul></div>}
            {analysis.verification_note && <small className="simple-verification-note">{analysis.verification_note}</small>}
          </> : <p className="simple-analysis-loading">{analysisBusyId === job.id ? 'Comparing the job with your saved resume…' : 'Open “Why this match?” to request a detailed comparison.'}</p>}
          {job.qualification_reasons?.length > 0 && <div className="simple-qualification-reasons"><strong>Why this listing qualified</strong><ul>{job.qualification_reasons.map((reason, i) => <li key={`${job.id}-qualified-${i}`}>{reason}</li>)}</ul></div>}
          {job.required_skills?.length > 0 && <div className="simple-required-skills"><strong>Skills mentioned in the listing</strong><span>{job.required_skills.join(' · ')}</span></div>}
          <div className="simple-original-link"><strong>Original listing</strong><a href={job.source_url} target="_blank" rel="noopener noreferrer">{job.source_url}</a></div>
        </div>}
      </article>;
    })}
  </div>;
}

function SearchFilters({ region, setRegion, customLocation, setCustomLocation, selectedWorkModes, setSelectedWorkModes, selectedEmploymentTypes, setSelectedEmploymentTypes, compact = false }) {
  const toggle = (items, setter, key) => {
    if (items.includes(key)) {
      if (items.length > 1) setter(items.filter(item => item !== key));
    } else {
      setter([...items, key]);
    }
  };
  return <div className={`search-filter-panel ${compact ? 'search-filter-panel-compact' : ''}`}>
    <div className="search-filter-topline"><div><span className="filter-section-kicker">LOCATION & WORK PREFERENCES</span><strong>Where and how would you like to work?</strong></div><span className="filter-selected-count">{selectedWorkModes.length + selectedEmploymentTypes.length} preferences active</span></div>
    <div className="search-region-fields">
      <label><span>Search region</span><select value={region} onChange={event => setRegion(event.target.value)}>{SEARCH_REGIONS.map(option => <option key={option.key} value={option.key}>{option.label}</option>)}</select></label>
      {region === 'custom' && <label><span>City, country, or region <b>*</b></span><input required value={customLocation} onChange={event => setCustomLocation(event.target.value)} placeholder="e.g. Bengaluru, UAE, Germany" maxLength={200}/></label>}
      <p className="region-filter-hint">Region filters apply to returned listings. Coverage depends on each enabled provider; generic remote roles may need eligibility verification.</p>
    </div>
    <div className="search-filter-groups">
      <fieldset className="search-filter-group"><legend>Work arrangement</legend><div className="filter-chip-list">{WORK_MODE_OPTIONS.map(option => <label key={option.key} className={`filter-chip ${selectedWorkModes.includes(option.key) ? 'selected' : ''}`}><input type="checkbox" checked={selectedWorkModes.includes(option.key)} onChange={() => toggle(selectedWorkModes, setSelectedWorkModes, option.key)}/><span>{option.label}</span></label>)}</div><button type="button" className="filter-select-all" onClick={() => setSelectedWorkModes(ALL_WORK_MODE_KEYS)}>Select all arrangements</button></fieldset>
      <fieldset className="search-filter-group"><legend>Employment type</legend><div className="filter-chip-list">{EMPLOYMENT_TYPE_OPTIONS.map(option => <label key={option.key} className={`filter-chip ${selectedEmploymentTypes.includes(option.key) ? 'selected' : ''}`}><input type="checkbox" checked={selectedEmploymentTypes.includes(option.key)} onChange={() => toggle(selectedEmploymentTypes, setSelectedEmploymentTypes, option.key)}/><span>{option.label}</span></label>)}</div><button type="button" className="filter-select-all" onClick={() => setSelectedEmploymentTypes(ALL_EMPLOYMENT_TYPE_KEYS)}>Select all employment types</button></fieldset>
    </div>
  </div>;
}

function ApplicationsView({ applications, analytics, navigate, updateStatus, generateAnswers, reviewAnswer, fillForm, applicationBusyId, autoSubmitEnabled, automationNote, agentError, setAgentError, agentReport, onApplyManually }) {
  const [filter, setFilter] = useState('all');
  const [expandedId, setExpandedId] = useState(null);
  const [answerEdits, setAnswerEdits] = useState({});
  const visible = filter === 'all' ? applications : applications.filter(app => app.status === filter);
  const statusOptions = [
    ['ready_for_review', 'Ready for review'], ['needs_manual_action', 'Needs manual action'], ['submitted', 'Submitted'],
    ['submitted_unconfirmed', 'Submitted · unconfirmed'], ['interview', 'Interview'], ['offer', 'Offer'],
    ['rejected', 'Rejected'], ['withdrawn', 'Withdrawn'], ['failed', 'Failed'], ['draft', 'Draft'],
  ];
  function parseAnswers(app) {
    try { const answers = JSON.parse(app.answers_json || '[]'); return Array.isArray(answers) ? answers : []; }
    catch { return []; }
  }
  return <div className="applications-workspace">
    <section className="application-analytics-grid">
      <div className="application-analytic-card"><span>Total tracked</span><strong>{analytics.total_applications || 0}</strong><small>Unique vacancies</small></div>
      <div className="application-analytic-card accent-teal"><span>Applied / submitted</span><strong>{analytics.submitted || 0}</strong><small>{analytics.applied_last_7_days || 0} in last 7 days</small></div>
      <div className="application-analytic-card accent-amber"><span>Needs review</span><strong>{analytics.awaiting_review || 0}</strong><small>Drafts or manual steps</small></div>
      <div className="application-analytic-card accent-violet"><span>Interviews / offers</span><strong>{(analytics.interviews || 0) + (analytics.offers || 0)}</strong><small>{analytics.interviews || 0} interviews · {analytics.offers || 0} offers</small></div>
    </section>

    <section className="content-panel application-history-panel">
      <div className="application-history-heading"><div><span className="section-overline">APPLICATION HISTORY</span><h2>Every opportunity, accounted for.</h2><p>Review prepared applications, update outcomes, and export the full history—including job URLs, dates, statuses, notes, and screening answers.</p></div><a className="button button-primary" href={`${API}/api/analytics/export.xlsx`}><FileSpreadsheet size={16}/> Download Excel</a></div>
      <div className="application-history-toolbar"><div className="application-filter-tabs"><button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>All <span>{applications.length}</span></button><button className={filter === 'ready_for_review' ? 'active' : ''} onClick={() => setFilter('ready_for_review')}>Review</button><button className={filter === 'submitted' ? 'active' : ''} onClick={() => setFilter('submitted')}>Submitted</button><button className={filter === 'interview' ? 'active' : ''} onClick={() => setFilter('interview')}>Interview</button><button className={filter === 'offer' ? 'active' : ''} onClick={() => setFilter('offer')}>Offer</button></div><span className="export-format-note"><Download size={13}/> .xlsx · 3 sheets</span></div>
      {agentError && <div className="inline-alert error-alert"><AlertCircle size={15}/>{agentError}<button className="icon-button" onClick={() => setAgentError('')} aria-label="Dismiss error"><X size={14}/></button></div>}
      {agentReport?.message && <div className="inline-alert success-alert"><CheckCircle2 size={15}/>{agentReport.message}</div>}{agentReport?.warnings?.length > 0 && <div className="inline-alert discovery-alert"><ShieldCheck size={15}/><ul>{agentReport.warnings.slice(0, 6).map((warning, index) => <li key={`apply-warning-${index}`}>{warning}</li>)}</ul></div>}
      {!visible.length ? <div className="application-empty"><div className="application-empty-icon"><FileCheck2 size={23}/></div><h3>No application records yet</h3><p>Search from Find & Apply, attach your CV, check the match score, then choose manual or supported automatic application.</p><button className="button button-primary" onClick={() => navigate('overview')}><Bot size={15}/> Run job agent</button></div> : <div className="application-record-list">{visible.map(app => {
        const answers = parseAnswers(app);
        const needsReviewCount = answers.filter(answer => answer.status !== 'verified').length;
        return <article className="application-record" key={app.id}>
          <div className="application-record-main"><div className="application-record-logo">{String(app.company || '?').slice(0, 1).toUpperCase()}</div><div className="application-record-title"><h3>{app.title}</h3><p>{app.company} <span>·</span> {app.location || 'Location not specified'}</p><div className="application-record-meta"><span className={`application-status status-${app.status}`}>{app.status.replaceAll('_', ' ')}</span><span className="application-platform">{app.platform || 'unknown source'}</span><span className="application-match">{app.match_score}% match</span><span>Added {new Date(app.created_at).toLocaleDateString()}</span></div></div><label className="application-status-control"><span>Status</span><select value={app.status} disabled={applicationBusyId === app.id} onChange={event => updateStatus(app.id, event.target.value)}>{statusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div>
          {app.submission_message && <p className="application-result-note"><ShieldCheck size={13}/>{app.submission_message}</p>}
          <div className="application-record-actions"><button className="button button-secondary small-button" disabled={applicationBusyId === app.id} onClick={() => onApplyManually?.(app)}><ExternalLink size={13}/> Apply manually</button><button className="button button-secondary small-button" disabled={applicationBusyId === app.id} onClick={() => { setExpandedId(expandedId === app.id ? null : app.id); if (!answers.length) generateAnswers(app.id); }}><WandSparkles size={13}/> {answers.length ? 'Review answers' : 'Draft screening answers'}{needsReviewCount > 0 && <span className="review-count">{needsReviewCount} review</span>}</button><button className="button button-secondary small-button" disabled={applicationBusyId === app.id} onClick={() => fillForm(app.id, false)}><Bot size={13}/>{applicationBusyId === app.id ? 'Working…' : 'Fill supported form'}</button><button className="button button-primary small-button" disabled={!autoSubmitEnabled || applicationBusyId === app.id} onClick={() => { if (window.confirm(`Proceed to fill and submit ${app.title} at ${app.company}? Please ensure all answers are verified. The agent will not bypass CAPTCHA or required manual checks.`)) fillForm(app.id, true); }} title={autoSubmitEnabled ? 'Fill and submit on supported sites after checks' : 'Enable AUTO_SUBMIT_ENABLED in backend/.env and restart first'}><CheckCircle2 size={13}/>Fill & submit</button></div>
          {expandedId === app.id && <div className="screening-answer-list"><div className="screening-answer-heading"><div><strong>Screening answer drafts</strong><span>{answers.length} questions · {needsReviewCount} need your confirmation</span></div><button className="button button-secondary small-button" onClick={() => generateAnswers(app.id)} disabled={applicationBusyId === app.id}><RefreshCw size={13}/> Regenerate drafts</button></div>{answers.length ? answers.map((answer, idx) => {
        const editKey = `${app.id}-${idx}`;
        const editedAnswer = Object.prototype.hasOwnProperty.call(answerEdits, editKey) ? answerEdits[editKey] : (answer.answer || '');
        return <div className="screening-answer-row" key={`${app.id}-${idx}`}><div className="screening-question"><span>Q{idx + 1}</span><strong>{answer.question}</strong><em className={`answer-status answer-${answer.status}`}>{answer.status.replaceAll('_', ' ')}</em></div><textarea className="screening-answer-edit" rows="3" value={editedAnswer} onChange={event => setAnswerEdits(previous => ({...previous, [editKey]: event.target.value}))} placeholder="Review or write your answer based on your real experience…"/><small>Source: {answer.source || 'Not available'} · Confidence: {answer.confidence || 'low'}</small><div className="screening-answer-actions"><button className="button button-secondary small-button" disabled={applicationBusyId === app.id || !editedAnswer.trim()} onClick={() => reviewAnswer(app.id, idx, editedAnswer, 'draft')}>Save draft</button><button className="button button-primary small-button" disabled={applicationBusyId === app.id || !editedAnswer.trim() || answer.status === 'verified'} onClick={async () => { const success = await reviewAnswer(app.id, idx, editedAnswer, 'verified'); if (success) setAnswerEdits(previous => { const next = {...previous}; delete next[editKey]; return next; }); }}><CheckCircle2 size={13}/>{answer.status === 'verified' ? 'Verified' : 'I reviewed this answer'}</button></div></div>;
      }) : <p className="screening-empty">No answers yet. Generate draft answers from your saved profile and resume.</p>}</div>}
        </article>;
      })}</div>}
      <div className="application-privacy-foot"><ShieldCheck size={14}/><span>Excel export contains your application records and screening answers. Keep the downloaded file private. Auto-submit is off by default and is limited to supported sites.</span></div>
    </section>
    <section className="content-panel application-platform-coverage"><div className="coverage-icon"><Globe2 size={18}/></div><div><strong>Source coverage and application automation</strong><p>The job agent searches enabled Greenhouse/Lever company boards plus public aggregators (Arbeitnow, Remote OK, Jobicy, Himalayas, and Adzuna when credentials are supplied). JobSpy is an optional experimental connector that must be separately installed and enabled. Browser form filling is allowlisted for supported Greenhouse/Lever application pages. LinkedIn, Naukri, Indeed and other websites still need a permitted API or platform-specific adapter. CAPTCHA, identity checks, unknown screening questions, and unsupported required fields are handed back to you.</p><small>Auto-submit configured on this backend: <b>{autoSubmitEnabled ? 'Enabled' : 'Disabled'}</b>. {automationNote}</small></div></section>
  </div>;
}

const PROFILE_TABS = [
  { id: 'overview', label: 'Overview & resume' },
  { id: 'experience', label: 'Employment' },
  { id: 'education', label: 'Education & IT skills' },
  { id: 'projects', label: 'Projects & credentials' },
  { id: 'career', label: 'Career preferences' },
  { id: 'personal', label: 'Personal details' },
];

const ARRAY_SECTIONS = {
  employment_history_json: {
    title: 'Employment history', description: 'Add each role with dates, responsibilities, and measurable outcomes.',
    button: 'Add employment', empty: 'Add your current and previous roles.',
    fields: [
      { key: 'title', label: 'Job title' }, { key: 'company', label: 'Company' },
      { key: 'period', label: 'Employment period' }, { key: 'employment_type', label: 'Employment type' },
      { key: 'location', label: 'Location' }, { key: 'description', label: 'Responsibilities and achievements', multiline: true },
    ], defaults: { title: '', company: '', period: '', employment_type: 'Full-time', location: '', description: '' },
  },
  education_json: {
    title: 'Education', description: 'Add degrees, diplomas, institutions, and dates.', button: 'Add education', empty: 'Add your educational qualifications.',
    fields: [{ key: 'qualification', label: 'Qualification' }, { key: 'institution', label: 'Institution' }, { key: 'period', label: 'Years / period' }, { key: 'education_type', label: 'Study type' }],
    defaults: { qualification: '', institution: '', period: '', education_type: 'Full-time' },
  },
  it_skills_json: {
    title: 'IT skills', description: 'Add technical and professional skills with practical experience.', button: 'Add skill', empty: 'Add skills such as Boolean search, LinkedIn Recruiter, Python, or SQL.',
    fields: [{ key: 'skill', label: 'Skill' }, { key: 'version', label: 'Version' }, { key: 'last_used', label: 'Last used' }, { key: 'experience', label: 'Experience (e.g. 3 years)' }],
    defaults: { skill: '', version: '', last_used: '', experience: '' },
  },
  projects_json: {
    title: 'Projects', description: 'Add relevant projects, contributions, and portfolio links.', button: 'Add project', empty: 'Projects are optional, but useful for showing work samples.',
    fields: [{ key: 'name', label: 'Project name' }, { key: 'description', label: 'What you did', multiline: true }, { key: 'url', label: 'Project URL', type: 'url' }],
    defaults: { name: '', description: '', url: '' },
  },
  online_profiles_json: {
    title: 'Online profiles', description: 'LinkedIn, GitHub, personal website, or other professional profiles.', button: 'Add profile', empty: 'Add public professional profile links.',
    fields: [{ key: 'label', label: 'Profile type / name' }, { key: 'url', label: 'URL', type: 'url' }], defaults: { label: 'LinkedIn', url: '' },
  },
  work_samples_json: {
    title: 'Work samples', description: 'Link relevant work samples or portfolio material.', button: 'Add work sample', empty: 'Add a link and short name for a relevant work sample.',
    fields: [{ key: 'name', label: 'Work sample' }, { key: 'url', label: 'URL', type: 'url' }, { key: 'duration', label: 'Duration / date' }], defaults: { name: '', url: '', duration: '' },
  },
  publications_json: {
    title: 'White papers / research / publications', description: 'Add research papers, articles, and journal entries.', button: 'Add publication', empty: 'Add published research or articles if applicable.',
    fields: [{ key: 'title', label: 'Title' }, { key: 'publisher', label: 'Publisher / journal' }, { key: 'url', label: 'URL', type: 'url' }, { key: 'date', label: 'Date' }], defaults: { title: '', publisher: '', url: '', date: '' },
  },
  presentations_json: {
    title: 'Presentations', description: 'Add slide decks, talks, or presentations.', button: 'Add presentation', empty: 'Add any relevant presentation links.',
    fields: [{ key: 'title', label: 'Presentation title' }, { key: 'url', label: 'URL', type: 'url' }, { key: 'date', label: 'Date' }], defaults: { title: '', url: '', date: '' },
  },
  patents_json: {
    title: 'Patents', description: 'Optional patent details.', button: 'Add patent', empty: 'Add a patent if applicable.',
    fields: [{ key: 'title', label: 'Patent title' }, { key: 'details', label: 'Details / reference number', multiline: true }, { key: 'url', label: 'Public link', type: 'url' }], defaults: { title: '', details: '', url: '' },
  },
  certifications_json: {
    title: 'Certifications', description: 'Add certificates, issuing organizations, credential links, and validity.', button: 'Add certification', empty: 'Add training or professional certifications.',
    fields: [{ key: 'name', label: 'Certification' }, { key: 'issuer', label: 'Issuing organization' }, { key: 'credential_url', label: 'Credential URL', type: 'url' }, { key: 'validity', label: 'Validity / date' }], defaults: { name: '', issuer: '', credential_url: '', validity: '' },
  },
  languages_json: {
    title: 'Languages', description: 'List languages and reading, writing, and speaking proficiency.', button: 'Add language', empty: 'Add languages you can use professionally.',
    fields: [{ key: 'language', label: 'Language' }, { key: 'proficiency', label: 'Proficiency' }, { key: 'read', label: 'Read', type: 'checkbox' }, { key: 'write', label: 'Write', type: 'checkbox' }, { key: 'speak', label: 'Speak', type: 'checkbox' }],
    defaults: { language: '', proficiency: 'Professional', read: true, write: true, speak: true },
  },
};

function safeJsonObject(value) {
  try { const parsed = JSON.parse(value || '{}'); return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}; }
  catch { return {}; }
}
function safeJsonArray(value) {
  try { const parsed = JSON.parse(value || '[]'); return Array.isArray(parsed) ? parsed : []; }
  catch { return []; }
}
function updateJsonObject(profile, setProfile, field, key, value) {
  const current = safeJsonObject(profile[field]);
  setProfile({ ...profile, [field]: JSON.stringify({ ...current, [key]: value }) });
}

function ArrayEditor({ profile, setProfile, field }) {
  const section = ARRAY_SECTIONS[field];
  const items = safeJsonArray(profile[field]);
  const change = (index, key, value) => {
    const next = items.map((item, i) => i === index ? { ...item, [key]: value } : item);
    setProfile({ ...profile, [field]: JSON.stringify(next) });
  };
  const remove = index => setProfile({ ...profile, [field]: JSON.stringify(items.filter((_, i) => i !== index)) });
  const add = () => setProfile({ ...profile, [field]: JSON.stringify([...items, { ...section.defaults }]) });
  return <section className="profile-data-section">
    <div className="profile-data-heading"><div><h3>{section.title}</h3><p>{section.description}</p></div><button type="button" className="button button-secondary small-button" onClick={add}><Plus size={14}/>{section.button}</button></div>
    {items.length === 0 && <div className="profile-empty-row"><FileText size={17}/><span>{section.empty}</span></div>}
    <div className="repeat-list">{items.map((item, index) => <div className="repeat-card" key={`${field}-${index}`}>
      <div className="repeat-card-top"><strong>{item[section.fields[0].key]?.trim() || `${section.title.replace(/s$/, '')} ${index + 1}`}</strong><button className="icon-button repeat-remove" type="button" onClick={() => remove(index)} aria-label={`Remove ${section.title} item ${index + 1}`}><Trash2 size={14}/></button></div>
      <div className="repeat-fields">{section.fields.map(spec => spec.type === 'checkbox' ? <label className="repeat-check" key={spec.key}><input type="checkbox" checked={Boolean(item[spec.key])} onChange={event => change(index, spec.key, event.target.checked)}/><span>{spec.label}</span></label> : <label key={spec.key}>{spec.label}{spec.multiline ? <textarea rows="2" value={item[spec.key] || ''} onChange={event => change(index, spec.key, event.target.value)} placeholder={spec.label}/> : <input type={spec.type || 'text'} value={item[spec.key] || ''} onChange={event => change(index, spec.key, event.target.value)} placeholder={spec.label}/>}</label>)}</div>
    </div>)}</div>
  </section>;
}

function ObjectFieldsEditor({ profile, setProfile, field, title, description, fields }) {
  const values = safeJsonObject(profile[field]);
  return <section className="profile-data-section">
    <div className="profile-data-heading"><div><h3>{title}</h3><p>{description}</p></div></div>
    <div className="field-grid">{fields.map(spec => <label key={spec.key}>{spec.label}{spec.multiline ? <textarea rows="2" value={values[spec.key] || ''} onChange={event => updateJsonObject(profile, setProfile, field, spec.key, event.target.value)} placeholder={spec.label}/> : spec.options ? <select value={values[spec.key] || ''} onChange={event => updateJsonObject(profile, setProfile, field, spec.key, event.target.value)}><option value="">Not provided</option>{spec.options.map(option => <option key={option} value={option}>{option}</option>)}</select> : <input type={spec.type || 'text'} value={values[spec.key] || ''} onChange={event => updateJsonObject(profile, setProfile, field, spec.key, event.target.value)} placeholder={spec.label}/>}</label>)}</div>
  </section>;
}

function ProfileView({ profile, setProfile, saveProfile, saving, message, completion, uploadResume, resumeUploading, deleteResume, resumeDeleting, resumeMessage, resumePreview, showResumePreview, setShowResumePreview, loadResumeText }) {
  const [tab, setTab] = useState('overview');
  const [dragging, setDragging] = useState(false);
  const [resumeSuggestions, setResumeSuggestions] = useState(null);
  const [suggestionBusy, setSuggestionBusy] = useState(false);
  const [photoBusy, setPhotoBusy] = useState(false);
  const [photoMessage, setPhotoMessage] = useState('');
  const chooseFile = event => { const file = event.target.files?.[0]; if (file) uploadResume(file); event.target.value = ''; };
  const sizeLabel = profile.resume_size_bytes ? `${(profile.resume_size_bytes / 1024).toFixed(0)} KB` : '';
  async function createSuggestions() {
    setSuggestionBusy(true);
    setResumeMessage('');
    try {
      const response = await fetch(`${API}/api/profile/resume/suggestions`, { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(data.detail, response.status, 'Could not create suggestions'));
      setResumeSuggestions(data);
      setResumeMessage(data.note || 'Suggestions are ready. Review before using them.');
    } catch (error) {
      setResumeMessage(error.message || 'Could not create profile suggestions.');
    } finally { setSuggestionBusy(false); }
  }
  function applySuggestions() {
    if (!resumeSuggestions) return;
    setProfile({ ...profile,
      resume_headline: resumeSuggestions.headline || profile.resume_headline,
      profile_summary: resumeSuggestions.profile_summary || profile.profile_summary,
      skills: resumeSuggestions.skills || profile.skills,
    });
    setTab('overview');
    setResumeMessage('Suggestions copied into your profile fields. Review and save your changes.');
  }
  async function uploadPhoto(file) {
    if (!file) return;
    setPhotoMessage('');
    if (file.size > 2 * 1024 * 1024) { setPhotoMessage('Profile photo must be 2 MB or smaller.'); return; }
    const formData = new FormData();
    formData.append('file', file);
    setPhotoBusy(true);
    try {
      const response = await fetch(`${API}/api/profile/photo`, { method: 'POST', body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(data.detail, response.status, 'Could not upload photo'));
      const profileResponse = await fetch(`${API}/api/profile`);
      if (profileResponse.ok) setProfile({ ...DEFAULT_PROFILE, ...await profileResponse.json() });
      setPhotoMessage(`Photo uploaded: ${data.filename}`);
    } catch (error) { setPhotoMessage(error.message || 'Could not upload photo.'); }
    finally { setPhotoBusy(false); }
  }
  async function removePhoto() {
    setPhotoBusy(true);
    setPhotoMessage('');
    try {
      const response = await fetch(`${API}/api/profile/photo`, { method: 'DELETE' });
      const data = response.status === 204 ? null : await response.json();
      if (!response.ok) throw new Error(data?.detail || 'Could not remove photo');
      const profileResponse = await fetch(`${API}/api/profile`);
      if (profileResponse.ok) setProfile({ ...DEFAULT_PROFILE, ...await profileResponse.json() });
      setPhotoMessage('Profile photo removed.');
    } catch (error) { setPhotoMessage(error.message || 'Could not remove photo.'); }
    finally { setPhotoBusy(false); }
  }
  const statusLabel = profile.resume_parse_status === 'text_extracted' ? 'Text extracted' : profile.resume_parse_status === 'uploaded_no_selectable_text' ? 'Uploaded · no selectable text' : profile.resume_parse_status === 'uploaded_extraction_not_supported_for_legacy_doc' ? 'Uploaded · text extraction unavailable for DOC' : 'Uploaded';
  return <div className="profile-workspace">
    <div className="profile-intro-row"><div className="profile-form-intro"><div className="profile-big-avatar">{profile.photo_original_filename ? <img src={`${API}/api/profile/photo?v=${encodeURIComponent(profile.photo_uploaded_at || '')}`} alt="Profile portrait"/> : getInitials(profile.full_name)}</div><div><span className="section-overline">CANDIDATE PROFILE</span><h2>Your professional profile</h2><p>Build a reusable profile once. AI Job Hunter can use these facts for matching and application drafts later.</p></div></div><div className="profile-completion-mini"><strong>{completion}%</strong><span>complete</span><div className="strength-track"><div style={{ width: `${completion}%` }}/></div></div></div>
    <div className="profile-tabs" role="tablist" aria-label="Profile sections">{PROFILE_TABS.map(item => <button key={item.id} type="button" role="tab" aria-selected={tab === item.id} className={tab === item.id ? 'active' : ''} onClick={() => setTab(item.id)}>{item.label}</button>)}</div>
    <form className="profile-detail-form" onSubmit={saveProfile}>
      {tab === 'overview' && <div className="profile-tab-content">
        <div className="content-panel resume-upload-panel"><div className="resume-panel-heading"><div className="resume-file-icon"><FileText size={22}/></div><div><span className="section-overline">RESUME ATTACHMENT</span><h3>Upload your latest resume</h3><p>PDF, DOC, DOCX, or RTF · Maximum 2 MB. Files stay on this computer in local mode.</p></div></div>
          {profile.resume_original_filename ? <div className="uploaded-resume-row"><div className="uploaded-file-badge"><FileCheck2 size={20}/></div><div className="uploaded-file-info"><strong>{profile.resume_original_filename}</strong><span>{sizeLabel}{profile.resume_uploaded_at ? ` · Uploaded ${new Date(profile.resume_uploaded_at).toLocaleDateString()}` : ''} · {statusLabel}</span></div><a className="button button-secondary small-button" href={`${API}/api/profile/resume/download`}><ExternalLink size={13}/>Download</a><button type="button" className="icon-button repeat-remove" aria-label="Delete resume" disabled={resumeDeleting} onClick={deleteResume}>{resumeDeleting ? <RefreshCw size={14} className="spin-icon"/> : <Trash2 size={14}/>}</button></div> : <label className={`resume-dropzone ${dragging ? 'dragging' : ''}`} onDragOver={event => {event.preventDefault(); setDragging(true);}} onDragLeave={() => setDragging(false)} onDrop={event => {event.preventDefault(); setDragging(false); const file = event.dataTransfer.files?.[0]; if (file) uploadResume(file);}}><input type="file" accept=".pdf,.doc,.docx,.rtf,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/rtf" onChange={chooseFile} disabled={resumeUploading}/><span className="upload-cloud"><FileText size={22}/></span><strong>{resumeUploading ? 'Uploading and parsing…' : 'Drop your resume here or browse files'}</strong><span>Secure local upload · 2 MB max · PDF preferred</span></label>}
          {resumeMessage && <div className={`inline-alert ${resumeMessage.startsWith('Could not') || resumeMessage.startsWith('Resume must') ? 'error-alert' : 'success-alert'}`}>{resumeMessage.startsWith('Could not') || resumeMessage.startsWith('Resume must') ? <AlertCircle size={15}/> : <CheckCircle2 size={15}/>}<span>{resumeMessage}</span></div>}
          {profile.resume_original_filename && <div className="resume-actions-row"><div className="resume-action-buttons"><button className="button button-secondary small-button" type="button" onClick={() => { if (showResumePreview) setShowResumePreview(false); else if (resumePreview) setShowResumePreview(true); else loadResumeText(); }}><FileText size={14}/>{showResumePreview ? 'Hide extracted text' : 'Preview extracted text'}</button><button className="button button-primary small-button" type="button" onClick={createSuggestions} disabled={suggestionBusy}>{suggestionBusy ? <><RefreshCw size={13} className="spin-icon"/> Analysing…</> : <><WandSparkles size={13}/> Suggest profile details</>}</button></div><span>Suggestions are extracted locally and are not saved until you review and save the profile.</span></div>}
          {resumeSuggestions && <div className="resume-suggestions-box"><div><Sparkles size={15}/><strong>Suggested fields from your resume</strong></div><p><b>Headline:</b> {resumeSuggestions.headline || 'No confident headline found'}</p><p><b>Summary:</b> {resumeSuggestions.profile_summary || 'No summary paragraph confidently identified'}</p><p><b>Skills:</b> {resumeSuggestions.skills || 'No supported skill keywords found'}</p><button type="button" className="button button-secondary small-button" onClick={applySuggestions}>Use suggestions in profile</button></div>}
          {showResumePreview && <div className="resume-preview-box"><strong>Extracted text preview</strong><pre>{resumePreview || 'No selectable text was extracted. Scanned PDFs will need OCR in a later release.'}</pre></div>}
        </div>
        <div className="content-panel profile-form-panel"><div className="profile-photo-edit-row"><div className="profile-photo-large">{profile.photo_original_filename ? <img src={`${API}/api/profile/photo?v=${encodeURIComponent(profile.photo_uploaded_at || '')}`} alt="Profile portrait"/> : getInitials(profile.full_name)}</div><div className="profile-photo-edit-copy"><strong>Profile photo <span>Optional</span></strong><p>Use a clear professional photo. PNG, JPG, or WEBP · 2 MB max. Stored locally.</p><div className="profile-photo-actions"><label className="button button-secondary small-button">{photoBusy ? 'Working…' : profile.photo_original_filename ? 'Change photo' : 'Upload photo'}<input type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp" disabled={photoBusy} onChange={event => { const file = event.target.files?.[0]; if (file) uploadPhoto(file); event.target.value = ''; }}/></label>{profile.photo_original_filename && <button type="button" className="button button-secondary small-button" disabled={photoBusy} onClick={removePhoto}>Remove photo</button>}</div>{photoMessage && <small className={photoMessage.startsWith('Could not') || photoMessage.startsWith('Profile photo must') ? 'photo-error' : 'photo-success'}>{photoMessage}</small>}</div></div><div className="profile-section-title"><div><span className="section-overline">01 / PROFESSIONAL SUMMARY</span><h3>Basic information</h3><p>These are the core facts used for your job-match profile.</p></div></div><div className="profile-form">
          <div className="field-grid"><label>Full name<input value={profile.full_name || ''} onChange={event => setProfile({...profile, full_name: event.target.value})} placeholder="Your full name" autoComplete="name"/></label><label>Total experience (years)<input type="number" min="0" max="80" step="0.5" value={profile.years_experience ?? 0} onChange={event => setProfile({...profile, years_experience: Number(event.target.value)})}/></label></div>
          <label>Resume headline<input value={profile.resume_headline || ''} onChange={event => setProfile({...profile, resume_headline: event.target.value})} placeholder="IT & Non-IT Recruiter | Talent Acquisition Specialist"/></label>
          <label>Profile summary<textarea rows="4" value={profile.profile_summary || ''} onChange={event => setProfile({...profile, profile_summary: event.target.value})} placeholder="Summarize your experience, strengths, industries, and hiring markets…"/></label>
          <label>Target roles<input value={profile.target_titles || ''} onChange={event => setProfile({...profile, target_titles: event.target.value})} placeholder="Talent Acquisition Specialist, IT Recruiter…"/><small>Separate multiple target roles with commas.</small></label>
          <label>Key skills<input value={profile.skills || ''} onChange={event => setProfile({...profile, skills: event.target.value})} placeholder="End-to-end recruitment, Boolean search, LinkedIn Recruiter…"/><small>Separate skills with commas.</small></label>
          <label>Employment highlights<textarea rows="3" value={profile.employment_highlights || ''} onChange={event => setProfile({...profile, employment_highlights: event.target.value})} placeholder="Campus / fresher hiring, lateral hiring, leadership hiring…"/></label>
          <div className="verified-facts-box"><div className="verified-facts-title"><div className="facts-icon"><ShieldCheck size={17}/></div><div><strong>Verified facts for screening answers</strong><p>Optional. Only enter information you can confirm. Legal or conflict-of-interest questions will never be guessed.</p></div></div><label>Verified facts in JSON format<textarea className="json-input" rows="3" value={profile.verified_facts_json || '{}'} onChange={event => setProfile({...profile, verified_facts_json: event.target.value})} placeholder={'{\n  "notice_period": "30 days",\n  "work_authorization": "India"\n}'}/></label></div>
        </div></div>
      </div>}
      {tab === 'experience' && <div className="content-panel profile-form-panel"><ArrayEditor profile={profile} setProfile={setProfile} field="employment_history_json"/></div>}
      {tab === 'education' && <div className="content-panel profile-form-panel"><ArrayEditor profile={profile} setProfile={setProfile} field="education_json"/><ArrayEditor profile={profile} setProfile={setProfile} field="it_skills_json"/></div>}
      {tab === 'projects' && <div className="content-panel profile-form-panel"><ArrayEditor profile={profile} setProfile={setProfile} field="projects_json"/><ArrayEditor profile={profile} setProfile={setProfile} field="online_profiles_json"/><ArrayEditor profile={profile} setProfile={setProfile} field="work_samples_json"/><ArrayEditor profile={profile} setProfile={setProfile} field="publications_json"/><ArrayEditor profile={profile} setProfile={setProfile} field="presentations_json"/><ArrayEditor profile={profile} setProfile={setProfile} field="patents_json"/><ArrayEditor profile={profile} setProfile={setProfile} field="certifications_json"/></div>}
      {tab === 'career' && <div className="content-panel profile-form-panel"><ObjectFieldsEditor profile={profile} setProfile={setProfile} field="career_profile_json" title="Career profile" description="Define the roles, locations, schedule, and compensation range you prefer." fields={[{key:'current_industry',label:'Current industry'},{key:'department',label:'Department'},{key:'role_category',label:'Role category'},{key:'job_role',label:'Job role'},{key:'desired_job_type',label:'Desired job type',options:['Permanent','Contractual','Both']},{key:'desired_employment_type',label:'Employment type',options:['Full-time','Part-time','Contract','Internship','Any']},{key:'preferred_roles',label:'Preferred job roles',multiline:true},{key:'preferred_locations',label:'Preferred locations',multiline:true},{key:'preferred_annual_salary',label:'Desired annual salary (optional)'},{key:'preferred_shift',label:'Preferred shift',options:['Flexible','Day','Night','Rotational','Any']}]} /><div className="content-panel nested-profile-panel"><div className="field-grid"><label>Preferred locations used for matching<input value={profile.preferred_locations || ''} onChange={event => setProfile({...profile, preferred_locations: event.target.value})} placeholder="Remote, Delhi NCR, Bengaluru"/></label><label>Preferred work modes<select value={profile.preferred_work_modes || 'Remote, Hybrid, On-site'} onChange={event => setProfile({...profile, preferred_work_modes: event.target.value})}><option>Remote, Hybrid, On-site</option><option>Remote, Hybrid</option><option>Remote only</option><option>Hybrid, On-site</option><option>On-site only</option></select></label></div></div></div>}
      {tab === 'personal' && <div className="content-panel profile-form-panel"><div className="optional-privacy-note"><LockKeyhole size={17}/><div><strong>Optional personal information</strong><p>Only fill fields you want to maintain locally. These fields are not required for job matching, and should not be included in applications unless you choose to share them.</p></div></div><ObjectFieldsEditor profile={profile} setProfile={setProfile} field="personal_details_json" title="Personal details" description="Optional information similar to the sections available in common job-board profiles." fields={[{key:'email',label:'Email (optional)',type:'email'},{key:'phone',label:'Phone (optional)',type:'tel'},{key:'city',label:'City'},{key:'state',label:'State / province'},{key:'country',label:'Country'},{key:'postal_code',label:'Postal / ZIP code'},{key:'gender',label:'Gender',options:['Male','Female','Non-binary','Prefer not to say','Self-describe']},{key:'marital_status',label:'Marital status',options:['Single','Married','Prefer not to say']},{key:'date_of_birth',label:'Date of birth',type:'date'},{key:'category',label:'Category (optional)'},{key:'work_permit',label:'Work permit / authorization',multiline:true},{key:'address',label:'Address',multiline:true},{key:'diversity_disability_status',label:'Diversity / disability (optional)',multiline:true},{key:'military_experience',label:'Military experience (optional)'},{key:'career_break',label:'Career break details (optional)',multiline:true}]} /><ArrayEditor profile={profile} setProfile={setProfile} field="languages_json"/></div>}
      <div className="content-panel profile-save-bar"><div className="save-bar-copy"><LockKeyhole size={15}/><span>Saved on this device · Upload and profile data remain local</span></div><div className="save-bar-actions">{message && <span className={message.startsWith('Could not') ? 'save-error' : 'save-success'}>{message}</span>}<button className="button button-primary" type="submit" disabled={saving}>{saving ? <><RefreshCw size={14} className="spin-icon"/> Saving…</> : <><Check size={15}/> Save profile changes</>}</button></div></div>
    </form>
  </div>;
}


function SettingsView({ health, autoSubmitEnabled, automationNote }) {
  const [browserCheck, setBrowserCheck] = useState(null);
  const [checkingBrowser, setCheckingBrowser] = useState(false);
  async function runBrowserCheck() {
    setCheckingBrowser(true);
    setBrowserCheck(null);
    try {
      const response = await fetch(`${API}/api/automation/diagnostics`);
      const data = await readResponsePayload(response);
      if (!response.ok) throw new Error(apiErrorMessage(data.detail ?? data.message ?? data, response.status, 'Browser diagnostics failed'));
      setBrowserCheck(data);
    } catch (error) {
      setBrowserCheck({ ready: false, message: error.message || 'Could not run browser diagnostics.' });
    } finally { setCheckingBrowser(false); }
  }
  return <div className="settings-layout"><div className="content-panel settings-card"><div className="settings-heading"><div className="settings-icon"><Activity size={18}/></div><div><h2>Local environment</h2><p>Connection and local runtime status.</p></div></div><div className="setting-row"><div><strong>Backend API</strong><span>FastAPI on your local machine</span></div><span className={`setting-status ${health}`}>{health === 'online' ? 'Connected' : health === 'checking' ? 'Checking…' : 'Offline'}</span></div><div className="setting-row"><div><strong>Data storage</strong><span>SQLite · local database</span></div><span className="setting-status configured">Configured</span></div><div className="setting-row"><div><strong>Application submission</strong><span>{autoSubmitEnabled ? "Explicit auto-submit enabled by local configuration" : "Approval-first; auto-submit is disabled by default"}</span></div><span className={`setting-status ${autoSubmitEnabled ? "configured" : "disabled"}`}>{autoSubmitEnabled ? "Enabled" : "Disabled"}</span></div></div><div className="content-panel settings-card"><div className="settings-heading"><div className="settings-icon violet-setting"><Sparkles size={18}/></div><div><h2>AI provider</h2><p>Choose a local model or an OpenAI-compatible endpoint in backend/.env.</p></div></div><div className="provider-option"><div className="provider-logo ollama-logo">O</div><div><strong>Ollama local models</strong><span>Set AI_PROVIDER=ollama and configure OLLAMA_BASE_URL / OLLAMA_MODEL.</span></div><span className="roadmap-pill">AVAILABLE</span></div><div className="provider-option"><div className="provider-logo cloud-logo"><Globe2 size={17}/></div><div><strong>Cloud AI providers</strong><span>Set AI_PROVIDER=openai and add OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL.</span></div><span className="roadmap-pill">AVAILABLE</span></div></div><div className="content-panel settings-card"><div className="settings-heading"><div className="settings-icon violet-setting"><Activity size={18}/></div><div><h2>Browser automation readiness</h2><p>Check the same Python environment used by the running backend. This check does not open a browser or submit an application.</p></div></div><button className="button button-secondary small-button" type="button" onClick={runBrowserCheck} disabled={checkingBrowser}>{checkingBrowser ? <><RefreshCw size={13} className="spin-icon"/> Checking…</> : <><ShieldCheck size={14}/> Check browser setup</>}</button>{browserCheck && <div className={`browser-diagnostic-result ${browserCheck.ready ? 'is-ready' : 'needs-fix'}`}><strong>{browserCheck.ready ? 'Browser setup ready' : 'Browser setup needs attention'}</strong><p>{browserCheck.message}</p>{browserCheck.python_executable && <small>Backend Python: {browserCheck.python_executable}</small>}{browserCheck.event_loop_type && <small>Event loop: {browserCheck.event_loop_type} {browserCheck.event_loop_compatible === false ? '(incompatible with async Playwright on Windows)' : '(compatible)'}</small>}{browserCheck.chromium_path && <small>Chromium: {browserCheck.chromium_path}</small>}{browserCheck.install_command && !browserCheck.ready && <code>{browserCheck.install_command}</code>}</div>}</div><div className="content-panel settings-card"><div className="settings-heading"><div className="settings-icon amber-setting"><ShieldCheck size={18}/></div><div><h2>Privacy & automation</h2><p>Safety controls for the future job agent.</p></div></div><div className="setting-row"><div><strong>Submit applications automatically</strong><span>Set AUTO_SUBMIT_ENABLED=true in backend/.env and restart. Supported hosts and required-field checks still apply.</span></div><span className={`setting-status ${autoSubmitEnabled ? 'configured' : 'disabled'}`}>{autoSubmitEnabled ? 'Enabled via .env' : 'Disabled'}</span></div><div className="setting-row"><div><strong>Secrets and API keys</strong><span>Keep these in local environment variables, never source code.</span></div><span className="setting-status configured">Protected by Git ignore</span></div><p className="automation-settings-note">{automationNote}</p></div></div>;
}
