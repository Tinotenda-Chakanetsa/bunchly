/* Demo data mirrored from the Daybreak prototype's data.jsx. Used for
   pages whose backend endpoints aren't fully wired yet — keeps the
   visual fidelity of the prototype while the real API integrations
   land progressively. */

export const DEPARTMENTS = [
  { id: "eng", name: "Engineering", head: "Maya Okafor", count: 38, colorClass: "av-1" },
  { id: "design", name: "Design", head: "Felix Hartmann", count: 12, colorClass: "av-2" },
  { id: "sales", name: "Sales", head: "Priya Iyer", count: 24, colorClass: "av-3" },
  { id: "marketing", name: "Marketing", head: "Joseph Mensah", count: 14, colorClass: "av-4" },
  { id: "ops", name: "People Ops", head: "Nadia Chen", count: 9, colorClass: "av-5" },
  { id: "finance", name: "Finance", head: "Tomás Ribeiro", count: 11, colorClass: "av-6" },
  { id: "support", name: "Customer Success", head: "Aaliyah Brooks", count: 18, colorClass: "av-7" },
  { id: "legal", name: "Legal", head: "Ravi Kapoor", count: 5, colorClass: "av-8" },
];

export const LOCATIONS = ["Cape Town", "Johannesburg", "Nairobi", "Lagos", "London", "Remote"];

export interface DemoEmployee {
  id: string;
  name: string;
  title: string;
  dept: string;
  location: string;
  status: string;
  type: string;
  joined: string;
  manager: string | null;
  av: string;
  initials: string;
  probation: boolean;
  contractEnd: string | null;
  leaveBalance: number;
  email: string;
}

export const EMPLOYEES: DemoEmployee[] = [
  { id: "E-0101", name: "Maya Okafor", title: "Director of Engineering", dept: "Engineering", location: "Cape Town", status: "Active", type: "Full-time", joined: "2019-03-04", manager: null, av: "av-1", initials: "MO", probation: false, contractEnd: null, leaveBalance: 14, email: "maya.okafor@bunchly.io" },
  { id: "E-0102", name: "Felix Hartmann", title: "Head of Design", dept: "Design", location: "London", status: "Active", type: "Full-time", joined: "2020-08-12", manager: null, av: "av-2", initials: "FH", probation: false, contractEnd: null, leaveBalance: 9, email: "felix.h@bunchly.io" },
  { id: "E-0103", name: "Priya Iyer", title: "VP, Sales", dept: "Sales", location: "London", status: "Active", type: "Full-time", joined: "2018-01-22", manager: null, av: "av-3", initials: "PI", probation: false, contractEnd: null, leaveBalance: 21, email: "priya@bunchly.io" },
  { id: "E-0104", name: "Joseph Mensah", title: "Head of Marketing", dept: "Marketing", location: "Lagos", status: "Active", type: "Full-time", joined: "2021-04-19", manager: null, av: "av-4", initials: "JM", probation: false, contractEnd: null, leaveBalance: 12, email: "joseph@bunchly.io" },
  { id: "E-0105", name: "Nadia Chen", title: "Head of People", dept: "People Ops", location: "Cape Town", status: "Active", type: "Full-time", joined: "2017-06-01", manager: null, av: "av-5", initials: "NC", probation: false, contractEnd: null, leaveBalance: 18, email: "nadia@bunchly.io" },
  { id: "E-0106", name: "Tomás Ribeiro", title: "CFO", dept: "Finance", location: "London", status: "Active", type: "Full-time", joined: "2019-11-15", manager: null, av: "av-6", initials: "TR", probation: false, contractEnd: null, leaveBalance: 10, email: "tomas@bunchly.io" },
  { id: "E-0201", name: "Aiko Tanaka", title: "Senior Frontend Engineer", dept: "Engineering", location: "Remote", status: "Active", type: "Full-time", joined: "2022-02-14", manager: "Maya Okafor", av: "av-1", initials: "AT", probation: false, contractEnd: null, leaveBalance: 8, email: "aiko@bunchly.io" },
  { id: "E-0202", name: "Benjamin Cole", title: "Backend Engineer", dept: "Engineering", location: "Johannesburg", status: "Active", type: "Full-time", joined: "2023-09-01", manager: "Maya Okafor", av: "av-2", initials: "BC", probation: true, contractEnd: null, leaveBalance: 6, email: "ben@bunchly.io" },
  { id: "E-0203", name: "Chioma Eze", title: "DevOps Engineer", dept: "Engineering", location: "Lagos", status: "Active", type: "Full-time", joined: "2021-07-18", manager: "Maya Okafor", av: "av-3", initials: "CE", probation: false, contractEnd: null, leaveBalance: 11, email: "chioma@bunchly.io" },
  { id: "E-0204", name: "David Mwangi", title: "ML Engineer", dept: "Engineering", location: "Nairobi", status: "Active", type: "Contract", joined: "2024-03-15", manager: "Maya Okafor", av: "av-4", initials: "DM", probation: false, contractEnd: "2026-03-15", leaveBalance: 7, email: "david@bunchly.io" },
  { id: "E-0205", name: "Esi Asante", title: "Frontend Engineer", dept: "Engineering", location: "Cape Town", status: "Active", type: "Full-time", joined: "2023-01-09", manager: "Maya Okafor", av: "av-5", initials: "EA", probation: false, contractEnd: null, leaveBalance: 13, email: "esi@bunchly.io" },
  { id: "E-0206", name: "Farai Moyo", title: "Engineering Manager", dept: "Engineering", location: "Cape Town", status: "Active", type: "Full-time", joined: "2020-05-04", manager: "Maya Okafor", av: "av-6", initials: "FM", probation: false, contractEnd: null, leaveBalance: 5, email: "farai@bunchly.io" },
  { id: "E-0301", name: "Grace Adeyemi", title: "Senior Product Designer", dept: "Design", location: "Lagos", status: "Active", type: "Full-time", joined: "2022-08-22", manager: "Felix Hartmann", av: "av-1", initials: "GA", probation: false, contractEnd: null, leaveBalance: 9, email: "grace@bunchly.io" },
  { id: "E-0302", name: "Henry Pillay", title: "UX Researcher", dept: "Design", location: "Cape Town", status: "Active", type: "Full-time", joined: "2023-11-06", manager: "Felix Hartmann", av: "av-2", initials: "HP", probation: false, contractEnd: null, leaveBalance: 10, email: "henry@bunchly.io" },
  { id: "E-0303", name: "Iris Yamamoto", title: "Brand Designer", dept: "Design", location: "Remote", status: "On Leave", type: "Full-time", joined: "2021-12-01", manager: "Felix Hartmann", av: "av-3", initials: "IY", probation: false, contractEnd: null, leaveBalance: 22, email: "iris@bunchly.io" },
  { id: "E-0401", name: "James Botha", title: "Account Executive", dept: "Sales", location: "Cape Town", status: "Active", type: "Full-time", joined: "2023-04-11", manager: "Priya Iyer", av: "av-4", initials: "JB", probation: false, contractEnd: null, leaveBalance: 11, email: "james@bunchly.io" },
  { id: "E-0402", name: "Kemi Owusu", title: "Senior Account Executive", dept: "Sales", location: "Lagos", status: "Active", type: "Full-time", joined: "2021-09-22", manager: "Priya Iyer", av: "av-5", initials: "KO", probation: false, contractEnd: null, leaveBalance: 8, email: "kemi@bunchly.io" },
  { id: "E-0403", name: "Liam O'Connor", title: "SDR", dept: "Sales", location: "London", status: "Active", type: "Full-time", joined: "2024-01-08", manager: "Priya Iyer", av: "av-6", initials: "LO", probation: true, contractEnd: null, leaveBalance: 4, email: "liam@bunchly.io" },
  { id: "E-0501", name: "Mariana Silva", title: "Content Lead", dept: "Marketing", location: "Remote", status: "Active", type: "Full-time", joined: "2022-06-13", manager: "Joseph Mensah", av: "av-7", initials: "MS", probation: false, contractEnd: null, leaveBalance: 14, email: "mariana@bunchly.io" },
  { id: "E-0502", name: "Noah Kruger", title: "Growth Manager", dept: "Marketing", location: "Johannesburg", status: "Active", type: "Full-time", joined: "2023-02-20", manager: "Joseph Mensah", av: "av-8", initials: "NK", probation: false, contractEnd: null, leaveBalance: 9, email: "noah@bunchly.io" },
  { id: "E-0601", name: "Olamide Diallo", title: "Senior People Partner", dept: "People Ops", location: "Lagos", status: "Active", type: "Full-time", joined: "2020-10-15", manager: "Nadia Chen", av: "av-1", initials: "OD", probation: false, contractEnd: null, leaveBalance: 12, email: "olamide@bunchly.io" },
  { id: "E-0602", name: "Pia Lindberg", title: "People Operations Lead", dept: "People Ops", location: "London", status: "Active", type: "Full-time", joined: "2021-03-29", manager: "Nadia Chen", av: "av-2", initials: "PL", probation: false, contractEnd: null, leaveBalance: 15, email: "pia@bunchly.io" },
  { id: "E-0701", name: "Quentin Rivière", title: "Financial Analyst", dept: "Finance", location: "London", status: "Active", type: "Full-time", joined: "2022-11-07", manager: "Tomás Ribeiro", av: "av-3", initials: "QR", probation: false, contractEnd: null, leaveBalance: 11, email: "quentin@bunchly.io" },
  { id: "E-0702", name: "Rasha Khalil", title: "Payroll Officer", dept: "Finance", location: "Cape Town", status: "Active", type: "Full-time", joined: "2023-08-01", manager: "Tomás Ribeiro", av: "av-4", initials: "RK", probation: false, contractEnd: null, leaveBalance: 7, email: "rasha@bunchly.io" },
  { id: "E-0801", name: "Sofia Romano", title: "Senior CS Manager", dept: "Customer Success", location: "London", status: "Active", type: "Full-time", joined: "2021-05-17", manager: "Aaliyah Brooks", av: "av-5", initials: "SR", probation: false, contractEnd: null, leaveBalance: 13, email: "sofia@bunchly.io" },
  { id: "E-0802", name: "Tariq Hassan", title: "CS Specialist", dept: "Customer Success", location: "Cape Town", status: "Active", type: "Full-time", joined: "2024-08-19", manager: "Aaliyah Brooks", av: "av-6", initials: "TH", probation: true, contractEnd: null, leaveBalance: 3, email: "tariq@bunchly.io" },
];

export const LEAVE_TYPES = [
  { id: "annual", name: "Annual leave", days: 21, color: "var(--action)" },
  { id: "sick", name: "Sick leave", days: 10, color: "var(--danger)" },
  { id: "study", name: "Study leave", days: 5, color: "var(--bunchly)" },
  { id: "maternity", name: "Maternity", days: 120, color: "var(--yellow)" },
  { id: "compassionate", name: "Compassionate", days: 5, color: "#7B5BFF" },
];

export interface DemoLeaveRequest {
  id: string;
  who: string;
  av: string;
  type: string;
  start: string;
  end: string;
  days: number;
  status: string;
  stage: string;
  manager: string;
  reason: string;
  submittedAt: string;
}

export const LEAVE_REQUESTS: DemoLeaveRequest[] = [
  { id: "LR-0042", who: "Aiko Tanaka", av: "av-1", type: "Annual", start: "2026-06-02", end: "2026-06-09", days: 6, status: "Pending Approval", stage: "Manager", manager: "Maya Okafor", reason: "Family holiday in Hokkaido — booked since January.", submittedAt: "2026-05-18" },
  { id: "LR-0041", who: "Benjamin Cole", av: "av-2", type: "Sick", start: "2026-05-20", end: "2026-05-21", days: 2, status: "Pending Approval", stage: "Manager", manager: "Maya Okafor", reason: "Flu — doctor's note attached.", submittedAt: "2026-05-20" },
  { id: "LR-0040", who: "Esi Asante", av: "av-5", type: "Annual", start: "2026-07-12", end: "2026-07-20", days: 7, status: "Pending Approval", stage: "Manager", manager: "Farai Moyo", reason: "Wedding in Accra.", submittedAt: "2026-05-15" },
  { id: "LR-0039", who: "Liam O'Connor", av: "av-6", type: "Annual", start: "2026-05-25", end: "2026-05-29", days: 5, status: "Pending HR", stage: "HR", manager: "Priya Iyer", reason: "Personal travel.", submittedAt: "2026-05-12" },
  { id: "LR-0038", who: "Iris Yamamoto", av: "av-3", type: "Maternity", start: "2026-04-01", end: "2026-08-01", days: 90, status: "Approved", stage: "Done", manager: "Felix Hartmann", reason: "Maternity leave.", submittedAt: "2026-02-15" },
  { id: "LR-0037", who: "Grace Adeyemi", av: "av-1", type: "Study", start: "2026-06-15", end: "2026-06-19", days: 5, status: "Approved", stage: "Done", manager: "Felix Hartmann", reason: "Design systems certification.", submittedAt: "2026-05-01" },
  { id: "LR-0036", who: "Chioma Eze", av: "av-3", type: "Annual", start: "2026-08-04", end: "2026-08-15", days: 10, status: "Approved", stage: "Done", manager: "Maya Okafor", reason: "Annual family visit.", submittedAt: "2026-04-20" },
  { id: "LR-0035", who: "James Botha", av: "av-4", type: "Sick", start: "2026-05-08", end: "2026-05-09", days: 2, status: "Approved", stage: "Done", manager: "Priya Iyer", reason: "Flu.", submittedAt: "2026-05-08" },
  { id: "LR-0034", who: "Tariq Hassan", av: "av-6", type: "Annual", start: "2026-06-30", end: "2026-07-04", days: 5, status: "Rejected", stage: "Done", manager: "Aaliyah Brooks", reason: "Holiday — conflict with launch.", submittedAt: "2026-05-10" },
];

export const BIRTHDAYS = [
  { name: "Aiko Tanaka", av: "av-1", date: "May 21", age: 31, dept: "Engineering" },
  { name: "Pia Lindberg", av: "av-2", date: "May 23", age: 38, dept: "People Ops" },
  { name: "Joseph Mensah", av: "av-4", date: "May 25", age: 42, dept: "Marketing" },
  { name: "Mariana Silva", av: "av-7", date: "May 28", age: 29, dept: "Marketing" },
];

export const HOLIDAYS_UPCOMING = [
  { name: "Africa Day", date: "May 25, 2026", region: "ZA · KE · NG", weekday: "Mon" },
  { name: "Spring Bank Holiday", date: "May 26, 2026", region: "UK", weekday: "Mon" },
  { name: "Youth Day", date: "Jun 16, 2026", region: "ZA", weekday: "Tue" },
];

export const DOCUMENTS = [
  { id: "DOC-3201", name: "Employment contract — A. Tanaka.pdf", category: "Contract", owner: "Aiko Tanaka", uploaded: "2022-02-14", size: "284 KB", status: "Verified", confidential: true },
  { id: "DOC-3202", name: "ID Copy — B. Cole.pdf", category: "National ID", owner: "Benjamin Cole", uploaded: "2023-09-01", size: "1.2 MB", status: "Verified", confidential: true },
  { id: "DOC-3203", name: "Bank confirmation — D. Mwangi.pdf", category: "Banking Details", owner: "David Mwangi", uploaded: "2024-03-14", size: "190 KB", status: "Pending Review", confidential: true },
  { id: "DOC-3204", name: "Tax certificate 2025 — E. Asante.pdf", category: "Tax", owner: "Esi Asante", uploaded: "2025-02-28", size: "342 KB", status: "Verified", confidential: false },
  { id: "DOC-3205", name: "Resume — G. Adeyemi.pdf", category: "CV", owner: "Grace Adeyemi", uploaded: "2022-08-20", size: "612 KB", status: "Verified", confidential: false },
  { id: "DOC-3206", name: "Birth certificate — H. Pillay child.pdf", category: "Birth Certificate", owner: "Henry Pillay", uploaded: "2024-01-10", size: "428 KB", status: "Verified", confidential: true },
  { id: "DOC-3207", name: "School fees invoice T3 — H. Pillay.pdf", category: "School Fees Invoice", owner: "Henry Pillay", uploaded: "2026-05-10", size: "188 KB", status: "Pending Review", confidential: true },
  { id: "DOC-3208", name: "Code of Conduct v3.pdf", category: "Policy", owner: "Bunchly Inc.", uploaded: "2026-01-15", size: "920 KB", status: "Verified", confidential: false },
  { id: "DOC-3209", name: "Maternity policy 2026.pdf", category: "Policy", owner: "Bunchly Inc.", uploaded: "2026-03-04", size: "612 KB", status: "Verified", confidential: false },
  { id: "DOC-3210", name: "Sick note — B. Cole.pdf", category: "Medical Certificates", owner: "Benjamin Cole", uploaded: "2026-05-20", size: "92 KB", status: "Pending Review", confidential: true },
];

export const PIPELINE_STAGES = [
  "Applied",
  "Screening",
  "Shortlisted",
  "Interview",
  "Reference Check",
  "Offer",
  "Hired",
];

export const CANDIDATES = [
  { id: "C-1101", name: "Sasha Petrov", role: "Senior Backend Engineer", stage: "Interview", source: "LinkedIn", days: 12, rating: 4, av: "av-1", expected: "$95k–$110k", location: "Remote" },
  { id: "C-1102", name: "Daniel Ofori", role: "Senior Backend Engineer", stage: "Shortlisted", source: "Referral · M. Okafor", days: 6, rating: 4, av: "av-2", expected: "$90k", location: "Lagos" },
  { id: "C-1103", name: "Yuki Mori", role: "Senior Backend Engineer", stage: "Screening", source: "Careers page", days: 2, rating: 3, av: "av-3", expected: "$100k", location: "Remote" },
  { id: "C-1104", name: "Hannah Park", role: "Product Designer II", stage: "Interview", source: "Dribbble", days: 9, rating: 5, av: "av-4", expected: "$80k", location: "London" },
  { id: "C-1105", name: "Mateo Vargas", role: "Product Designer II", stage: "Applied", source: "Careers page", days: 1, rating: null, av: "av-5", expected: "—", location: "Remote" },
  { id: "C-1106", name: "Renee Adebayo", role: "Product Designer II", stage: "Offer", source: "Referral · F. Hartmann", days: 21, rating: 5, av: "av-6", expected: "$78k", location: "Lagos" },
  { id: "C-1107", name: "Imani Sithole", role: "Account Executive", stage: "Shortlisted", source: "Careers page", days: 5, rating: 4, av: "av-7", expected: "$70k OTE", location: "Cape Town" },
  { id: "C-1108", name: "Alex Whitman", role: "Account Executive", stage: "Reference Check", source: "Recruiter", days: 18, rating: 4, av: "av-8", expected: "$75k OTE", location: "London" },
  { id: "C-1109", name: "Jin Park", role: "Account Executive", stage: "Hired", source: "LinkedIn", days: 30, rating: 5, av: "av-1", expected: "$72k OTE", location: "London" },
  { id: "C-1110", name: "Kabelo Sithole", role: "DevOps Engineer", stage: "Applied", source: "Careers page", days: 1, rating: null, av: "av-2", expected: "$85k", location: "Cape Town" },
  { id: "C-1111", name: "Mei Lin", role: "DevOps Engineer", stage: "Interview", source: "AngelList", days: 14, rating: 4, av: "av-3", expected: "$90k", location: "Remote" },
  { id: "C-1112", name: "Adaeze Okoro", role: "Marketing Manager", stage: "Applied", source: "Careers page", days: 3, rating: null, av: "av-4", expected: "$78k", location: "Lagos" },
];

export const JOB_REQS = [
  { id: "JR-208", title: "Senior Backend Engineer", dept: "Engineering", location: "Remote · EMEA", openings: 2, applicants: 47, status: "Open", posted: "2026-04-12", manager: "Maya Okafor" },
  { id: "JR-209", title: "Product Designer II", dept: "Design", location: "London / Hybrid", openings: 1, applicants: 31, status: "Open", posted: "2026-04-22", manager: "Felix Hartmann" },
  { id: "JR-210", title: "Account Executive — UK", dept: "Sales", location: "London / Hybrid", openings: 1, applicants: 22, status: "Offer", posted: "2026-03-30", manager: "Priya Iyer" },
  { id: "JR-211", title: "DevOps Engineer", dept: "Engineering", location: "Remote · Africa", openings: 1, applicants: 18, status: "Open", posted: "2026-05-02", manager: "Maya Okafor" },
  { id: "JR-212", title: "Marketing Manager", dept: "Marketing", location: "Lagos / Hybrid", openings: 1, applicants: 12, status: "Screening", posted: "2026-05-09", manager: "Joseph Mensah" },
  { id: "JR-213", title: "Senior People Partner", dept: "People Ops", location: "London / Hybrid", openings: 1, applicants: 0, status: "Draft", posted: null, manager: "Nadia Chen" },
];

export const ONBOARDING_PROGRAMMES = [
  { id: "OB-2026-05", name: "Benjamin Cole — Backend Engineer", startedAt: "2026-09-01", progress: 78, tasksDone: 14, tasksTotal: 18, manager: "Maya Okafor", av: "av-2" },
  { id: "OB-2026-04", name: "Liam O'Connor — SDR", startedAt: "2026-01-08", progress: 92, tasksDone: 23, tasksTotal: 25, manager: "Priya Iyer", av: "av-6" },
  { id: "OB-2026-03", name: "Tariq Hassan — CS Specialist", startedAt: "2024-08-19", progress: 56, tasksDone: 10, tasksTotal: 18, manager: "Aaliyah Brooks", av: "av-6" },
  { id: "OB-2026-06", name: "Jin Park — Account Executive", startedAt: "2026-06-01", progress: 12, tasksDone: 2, tasksTotal: 18, manager: "Priya Iyer", av: "av-1" },
];

export const ONBOARDING_TASKS_TPL = [
  { phase: "Before day 1", tasks: ["Send welcome email", "Order equipment", "Set up Slack & Google Workspace", "Manager intro call"] },
  { phase: "Day 1", tasks: ["Office tour / virtual welcome", "Complete I-9 / right-to-work", "Code of conduct acknowledgement", "Meet buddy"] },
  { phase: "Week 1", tasks: ["1:1 with manager", "Read team handbook", "Complete security training", "Set 30-day goals"] },
  { phase: "Month 1", tasks: ["Shadow 3 teammates", "First ship", "30-day manager check-in", "Benefits enrolment"] },
  { phase: "Probation review", tasks: ["Self-assessment", "Manager review", "Confirmation letter"] },
];

export const PAYROLL_PERIODS = [
  { id: "PP-2026-05", period: "May 2026", status: "Processing", employees: 131, gross: "$1,284,200", net: "$948,710", cutoff: "2026-05-25", paydate: "2026-05-29" },
  { id: "PP-2026-04", period: "April 2026", status: "Paid", employees: 129, gross: "$1,261,400", net: "$932,180", cutoff: "2026-04-25", paydate: "2026-04-29" },
  { id: "PP-2026-03", period: "March 2026", status: "Paid", employees: 127, gross: "$1,248,900", net: "$921,640", cutoff: "2026-03-25", paydate: "2026-03-31" },
  { id: "PP-2026-02", period: "February 2026", status: "Paid", employees: 124, gross: "$1,201,300", net: "$889,440", cutoff: "2026-02-25", paydate: "2026-02-27" },
];

export const BENEFIT_TYPES = [
  { id: "BT-01", name: "Private medical cover", provider: "Discovery Health", enrolled: 118, eligible: 131, cost: "$148 / mo", waitDays: 0 },
  { id: "BT-02", name: "Pension (5% match)", provider: "Allan Gray", enrolled: 124, eligible: 131, cost: "5% match", waitDays: 90 },
  { id: "BT-03", name: "Education assistance", provider: "Bunchly", enrolled: 41, eligible: 131, cost: "Up to $2,400/child/yr", waitDays: 180 },
  { id: "BT-04", name: "Mental wellness — Spill", provider: "Spill", enrolled: 67, eligible: 131, cost: "$28 / mo", waitDays: 0 },
  { id: "BT-05", name: "Home office stipend", provider: "Bunchly", enrolled: 131, eligible: 131, cost: "$400 one-time", waitDays: 0 },
  { id: "BT-06", name: "Gym (ClassPass)", provider: "ClassPass", enrolled: 38, eligible: 131, cost: "$45 / mo", waitDays: 30 },
];

export const EDU_CLAIMS = [
  { id: "EC-0231", employee: "Henry Pillay", av: "av-2", child: "Anaya P. (8)", level: "Primary", institution: "Sunningdale Prep", period: "Term 2 2026", amount: 1240, status: "Pending HR", submitted: "2026-05-10", stage: "HR Review" },
  { id: "EC-0230", employee: "Aiko Tanaka", av: "av-1", child: "Kenji T. (14)", level: "Secondary", institution: "Tokyo Intl School", period: "Term 2 2026", amount: 2100, status: "Pending Payment", submitted: "2026-05-02", stage: "Accounts" },
  { id: "EC-0229", employee: "Olamide Diallo", av: "av-1", child: "Adaeze D. (19)", level: "Tertiary", institution: "UCT", period: "Semester 1 2026", amount: 2400, status: "Paid", submitted: "2026-02-12", stage: "Done" },
  { id: "EC-0228", employee: "Chioma Eze", av: "av-3", child: "Tobi E. (11)", level: "Primary", institution: "Greensprings", period: "Term 1 2026", amount: 1180, status: "Paid", submitted: "2026-02-04", stage: "Done" },
  { id: "EC-0227", employee: "Joseph Mensah", av: "av-4", child: "Kwame M. (16)", level: "Secondary", institution: "Loyola Jesuit", period: "Term 2 2026", amount: 1860, status: "Pending Payment", submitted: "2026-05-06", stage: "Accounts" },
  { id: "EC-0226", employee: "Mariana Silva", av: "av-7", child: "Luca S. (6)", level: "Primary", institution: "Escola Lumiar", period: "Term 2 2026", amount: 980, status: "Rejected", submitted: "2026-05-08", stage: "Done" },
  { id: "EC-0225", employee: "Priya Iyer", av: "av-3", child: "Aarav I. (10)", level: "Primary", institution: "Hampstead School", period: "Term 2 2026", amount: 1620, status: "Pending HR", submitted: "2026-05-14", stage: "HR Review" },
];

export const PERFORMANCE_REVIEWS = [
  { id: "PR-0091", who: "Aiko Tanaka", av: "av-1", cycle: "H1 2026", rating: 4.4, status: "Manager Review", manager: "Maya Okafor", due: "2026-06-10" },
  { id: "PR-0092", who: "Benjamin Cole", av: "av-2", cycle: "H1 2026", rating: null, status: "Self-Assessment", manager: "Maya Okafor", due: "2026-06-10" },
  { id: "PR-0093", who: "Grace Adeyemi", av: "av-1", cycle: "H1 2026", rating: 4.8, status: "Calibration", manager: "Felix Hartmann", due: "2026-06-12" },
  { id: "PR-0094", who: "Liam O'Connor", av: "av-6", cycle: "Probation", rating: 3.6, status: "Manager Review", manager: "Priya Iyer", due: "2026-06-08" },
  { id: "PR-0095", who: "Tariq Hassan", av: "av-6", cycle: "Probation", rating: 3.2, status: "At Risk", manager: "Aaliyah Brooks", due: "2026-06-05" },
  { id: "PR-0096", who: "Chioma Eze", av: "av-3", cycle: "H1 2026", rating: 4.6, status: "Complete", manager: "Maya Okafor", due: "2026-05-28" },
];

export const COURSES = [
  { id: "L-2001", title: "Security awareness 2026", category: "Compliance", duration: "45 min", enrolled: 131, complete: 118, mandatory: true, due: "2026-06-30" },
  { id: "L-2002", title: "Manager fundamentals", category: "Leadership", duration: "6 hrs", enrolled: 24, complete: 19, mandatory: false, due: null },
  { id: "L-2003", title: "POPIA & data privacy", category: "Compliance", duration: "1 hr", enrolled: 131, complete: 121, mandatory: true, due: "2026-07-15" },
  { id: "L-2004", title: "Public speaking essentials", category: "Soft skills", duration: "3 hrs", enrolled: 14, complete: 11, mandatory: false, due: null },
  { id: "L-2005", title: "Design systems with Bunchly UI", category: "Craft", duration: "4 hrs", enrolled: 12, complete: 6, mandatory: false, due: null },
  { id: "L-2006", title: "Anti-harassment training", category: "Compliance", duration: "1 hr", enrolled: 131, complete: 131, mandatory: true, due: "2026-12-31" },
];

export const ASSETS = [
  { id: "AST-0421", name: 'MacBook Pro 14" M3', category: "Laptop", serial: "C02XX9KZJG5L", assignedTo: "Aiko Tanaka", av: "av-1", condition: "Excellent", since: "2024-02-14" },
  { id: "AST-0422", name: "MacBook Air M3", category: "Laptop", serial: "C02RD4LMHV23", assignedTo: "Benjamin Cole", av: "av-2", condition: "Excellent", since: "2023-09-01" },
  { id: "AST-0423", name: "Dell U2723QE Monitor", category: "Monitor", serial: "5CG2491P7Q", assignedTo: "Esi Asante", av: "av-5", condition: "Good", since: "2023-01-10" },
  { id: "AST-0424", name: "iPhone 15", category: "Phone", serial: "F2LN18KZQ3", assignedTo: "Priya Iyer", av: "av-3", condition: "Excellent", since: "2024-09-22" },
  { id: "AST-0425", name: 'MacBook Pro 14" M2', category: "Laptop", serial: "C02XX0KZJG5L", assignedTo: null, av: null, condition: "Refurbished", since: null },
  { id: "AST-0426", name: "Logitech MX Master 3S", category: "Peripheral", serial: "2204LZ9F32", assignedTo: "Grace Adeyemi", av: "av-1", condition: "Excellent", since: "2024-08-22" },
];

export const HR_CASES = [
  { id: "HC-0312", subject: "Question about parental leave eligibility", category: "Benefits", priority: "Normal", status: "Open", raisedBy: "Mariana Silva", av: "av-7", sla: "On track", updated: "2 hours ago", assignee: "Olamide Diallo" },
  { id: "HC-0311", subject: "Update bank details", category: "Payroll", priority: "High", status: "In Progress", raisedBy: "Liam O'Connor", av: "av-6", sla: "On track", updated: "Yesterday", assignee: "Rasha Khalil" },
  { id: "HC-0310", subject: "Lost laptop charger", category: "Assets", priority: "Low", status: "Open", raisedBy: "Tariq Hassan", av: "av-6", sla: "Breach risk", updated: "3 days ago", assignee: null },
  { id: "HC-0309", subject: "Request flexible working arrangement", category: "Policy", priority: "Normal", status: "Awaiting Employee", raisedBy: "Quentin Rivière", av: "av-3", sla: "On track", updated: "4 days ago", assignee: "Pia Lindberg" },
  { id: "HC-0308", subject: "Reference letter for visa", category: "Documents", priority: "Normal", status: "Resolved", raisedBy: "David Mwangi", av: "av-4", sla: "Met", updated: "Last week", assignee: "Olamide Diallo" },
  { id: "HC-0307", subject: "Education claim — missing receipt", category: "Education assistance", priority: "High", status: "In Progress", raisedBy: "Henry Pillay", av: "av-2", sla: "On track", updated: "2 days ago", assignee: "Olamide Diallo" },
];

export const POLICIES = [
  { id: "POL-001", title: "Code of conduct", version: "v3.1", effective: "2026-01-15", category: "Conduct", acknowledged: 128, total: 131, mandatory: true },
  { id: "POL-002", title: "Remote work policy", version: "v2.0", effective: "2025-09-01", category: "Working arrangements", acknowledged: 131, total: 131, mandatory: true },
  { id: "POL-003", title: "Information security", version: "v4.2", effective: "2026-02-12", category: "IT & Security", acknowledged: 124, total: 131, mandatory: true },
  { id: "POL-004", title: "Education assistance benefit", version: "v1.4", effective: "2025-12-01", category: "Benefits", acknowledged: 131, total: 131, mandatory: false },
  { id: "POL-005", title: "Anti-harassment", version: "v2.1", effective: "2026-03-04", category: "Conduct", acknowledged: 131, total: 131, mandatory: true },
  { id: "POL-006", title: "Parental leave", version: "v3.0", effective: "2026-03-04", category: "Leave", acknowledged: 130, total: 131, mandatory: false },
];

export const AUDIT_LOGS = [
  { id: "AL-7821", at: "2026-05-21 10:42", actor: "Olamide Diallo", action: "Approved education claim", entity: "EC-0229", ip: "196.21.4.18" },
  { id: "AL-7820", at: "2026-05-21 10:31", actor: "Maya Okafor", action: "Approved leave request", entity: "LR-0036", ip: "41.66.21.4" },
  { id: "AL-7819", at: "2026-05-21 10:14", actor: "Rasha Khalil", action: "Marked payroll as paid", entity: "PP-2026-04", ip: "196.21.4.99" },
  { id: "AL-7818", at: "2026-05-21 09:58", actor: "Felix Hartmann", action: "Updated employee record", entity: "E-0301", ip: "82.12.4.55" },
  { id: "AL-7817", at: "2026-05-21 09:42", actor: "Nadia Chen", action: "Created job requisition", entity: "JR-213", ip: "41.66.21.4" },
  { id: "AL-7816", at: "2026-05-21 09:14", actor: "Priya Iyer", action: "Rejected leave request", entity: "LR-0034", ip: "82.12.4.55" },
  { id: "AL-7815", at: "2026-05-21 08:58", actor: "System", action: "Sent contract expiry reminders", entity: "Batch · 3", ip: "—" },
  { id: "AL-7814", at: "2026-05-20 17:14", actor: "Olamide Diallo", action: "Uploaded document", entity: "DOC-3210", ip: "196.21.4.18" },
  { id: "AL-7813", at: "2026-05-20 16:51", actor: "Esi Asante", action: "Submitted leave request", entity: "LR-0040", ip: "105.227.18.4" },
  { id: "AL-7812", at: "2026-05-20 16:22", actor: "System", action: "Daily birthday email batch sent", entity: "Batch · 1", ip: "—" },
];

export const ATTENDANCE_TODAY = [
  { who: "Aiko Tanaka", av: "av-1", in: "08:14", out: null, status: "Working", hours: "5h 32m" },
  { who: "Benjamin Cole", av: "av-2", in: "09:02", out: null, status: "Sick", hours: "—" },
  { who: "Chioma Eze", av: "av-3", in: "07:48", out: null, status: "Working", hours: "5h 58m" },
  { who: "Esi Asante", av: "av-5", in: "08:31", out: null, status: "Working", hours: "5h 15m" },
  { who: "Farai Moyo", av: "av-6", in: "08:55", out: null, status: "Working", hours: "4h 51m" },
  { who: "Grace Adeyemi", av: "av-1", in: "09:22", out: null, status: "Working", hours: "4h 24m" },
  { who: "Henry Pillay", av: "av-2", in: null, out: null, status: "Annual leave", hours: "—" },
];

export const NOTIFICATIONS = [
  { id: "N1", when: "12 min ago", title: "Aiko Tanaka requested leave", body: "6 days · 2 Jun → 9 Jun (Annual)", icon: "calendar", color: "yellow" },
  { id: "N2", when: "1 hr ago", title: "Education claim ready for payment", body: "Aiko Tanaka — $2,100 · School fees Term 2", icon: "money", color: "blue" },
  { id: "N3", when: "Today", title: "3 birthdays this week 🎉", body: "Aiko, Pia, Joseph", icon: "cake", color: "yellow" },
  { id: "N4", when: "Yesterday", title: "Probation ending soon", body: "Benjamin Cole — review by Jun 1", icon: "warn", color: "red" },
  { id: "N5", when: "2 days ago", title: "Contract renewal due", body: "David Mwangi — contract ends Mar 15, 2026", icon: "scroll", color: "blue" },
];
