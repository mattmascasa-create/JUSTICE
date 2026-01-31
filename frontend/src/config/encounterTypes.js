/**
 * Universal Encounter Types Configuration
 * 
 * Comprehensive list of encounter scenarios with officials, authorities,
 * and any situation where documentation could protect your rights.
 */

// ==================== ENCOUNTER CATEGORIES ====================

export const encounterCategories = [
  {
    id: 'law_enforcement',
    label: 'Law Enforcement',
    icon: 'shield',
    color: 'red',
    description: 'Police, sheriffs, federal agents'
  },
  {
    id: 'child_family',
    label: 'Child & Family Services',
    icon: 'users',
    color: 'purple',
    description: 'CPS, social workers, custody'
  },
  {
    id: 'government',
    label: 'Government Officials',
    icon: 'building',
    color: 'blue',
    description: 'Inspectors, immigration, IRS'
  },
  {
    id: 'legal',
    label: 'Legal Proceedings',
    icon: 'scale',
    color: 'amber',
    description: 'Court, depositions, hearings'
  },
  {
    id: 'medical',
    label: 'Medical & Healthcare',
    icon: 'heart-pulse',
    color: 'green',
    description: 'Hospitals, insurance, disputes'
  },
  {
    id: 'education',
    label: 'Education',
    icon: 'graduation-cap',
    color: 'indigo',
    description: 'Schools, disciplinary, IEP'
  },
  {
    id: 'workplace',
    label: 'Workplace',
    icon: 'briefcase',
    color: 'orange',
    description: 'HR, termination, investigations'
  },
  {
    id: 'housing',
    label: 'Housing',
    icon: 'home',
    color: 'teal',
    description: 'Landlords, evictions, inspections'
  },
  {
    id: 'accidents',
    label: 'Accidents & Incidents',
    icon: 'alert-triangle',
    color: 'yellow',
    description: 'Car accidents, injuries, property'
  },
  {
    id: 'consumer',
    label: 'Consumer & Business',
    icon: 'receipt',
    color: 'slate',
    description: 'Disputes, debt collectors, fraud'
  }
];

// ==================== ENCOUNTER TYPES ====================

export const universalEncounterTypes = [
  // === LAW ENFORCEMENT ===
  {
    value: 'traffic_stop',
    label: 'Traffic Stop',
    category: 'law_enforcement',
    icon: '🚗',
    description: 'Pulled over by police',
    severity: 'high'
  },
  {
    value: 'pedestrian_stop',
    label: 'Pedestrian Stop',
    category: 'law_enforcement',
    icon: '🚶',
    description: 'Stopped while walking',
    severity: 'high'
  },
  {
    value: 'home_visit_police',
    label: 'Police Home Visit',
    category: 'law_enforcement',
    icon: '🏠',
    description: 'Police at your door',
    severity: 'high'
  },
  {
    value: 'welfare_check',
    label: 'Welfare Check',
    category: 'law_enforcement',
    icon: '🔔',
    description: 'Police wellness check',
    severity: 'medium'
  },
  {
    value: 'arrest',
    label: 'Arrest',
    category: 'law_enforcement',
    icon: '⚠️',
    description: 'Being placed under arrest',
    severity: 'critical'
  },
  {
    value: 'search_seizure',
    label: 'Search / Seizure',
    category: 'law_enforcement',
    icon: '🔍',
    description: 'Property being searched',
    severity: 'critical'
  },
  {
    value: 'questioning',
    label: 'Police Questioning',
    category: 'law_enforcement',
    icon: '❓',
    description: 'Being questioned by police',
    severity: 'high'
  },
  {
    value: 'protest_demonstration',
    label: 'Protest / Demonstration',
    category: 'law_enforcement',
    icon: '✊',
    description: 'At a protest or march',
    severity: 'medium'
  },
  {
    value: 'dui_checkpoint',
    label: 'DUI Checkpoint',
    category: 'law_enforcement',
    icon: '🛑',
    description: 'Sobriety checkpoint stop',
    severity: 'medium'
  },

  // === CHILD & FAMILY SERVICES ===
  {
    value: 'cps_investigation',
    label: 'CPS Investigation',
    category: 'child_family',
    icon: '👨‍👩‍👧',
    description: 'Child Protective Services visit',
    severity: 'critical'
  },
  {
    value: 'cps_home_visit',
    label: 'CPS Home Visit',
    category: 'child_family',
    icon: '🏡',
    description: 'Scheduled or surprise CPS visit',
    severity: 'high'
  },
  {
    value: 'child_interview',
    label: 'Child Interview',
    category: 'child_family',
    icon: '👶',
    description: 'Officials interviewing your child',
    severity: 'critical'
  },
  {
    value: 'custody_exchange',
    label: 'Custody Exchange',
    category: 'child_family',
    icon: '🤝',
    description: 'Child custody handoff',
    severity: 'medium'
  },
  {
    value: 'supervised_visit',
    label: 'Supervised Visit',
    category: 'child_family',
    icon: '👁️',
    description: 'Court-ordered supervised visitation',
    severity: 'medium'
  },
  {
    value: 'family_court',
    label: 'Family Court',
    category: 'child_family',
    icon: '⚖️',
    description: 'Family court proceedings',
    severity: 'high'
  },

  // === GOVERNMENT OFFICIALS ===
  {
    value: 'ice_cbp',
    label: 'Immigration (ICE/CBP)',
    category: 'government',
    icon: '🛂',
    description: 'Immigration enforcement encounter',
    severity: 'critical'
  },
  {
    value: 'tsa_airport',
    label: 'TSA / Airport Security',
    category: 'government',
    icon: '✈️',
    description: 'Airport security screening',
    severity: 'medium'
  },
  {
    value: 'border_crossing',
    label: 'Border Crossing',
    category: 'government',
    icon: '🚧',
    description: 'US border or checkpoint',
    severity: 'high'
  },
  {
    value: 'irs_audit',
    label: 'IRS Audit / Visit',
    category: 'government',
    icon: '💰',
    description: 'Tax authority encounter',
    severity: 'high'
  },
  {
    value: 'code_enforcement',
    label: 'Code Enforcement',
    category: 'government',
    icon: '📋',
    description: 'City/county code inspector',
    severity: 'medium'
  },
  {
    value: 'building_inspector',
    label: 'Building Inspector',
    category: 'government',
    icon: '🏗️',
    description: 'Building/safety inspection',
    severity: 'low'
  },
  {
    value: 'health_inspector',
    label: 'Health Inspector',
    category: 'government',
    icon: '🏥',
    description: 'Health department visit',
    severity: 'medium'
  },
  {
    value: 'social_worker',
    label: 'Social Worker Visit',
    category: 'government',
    icon: '📝',
    description: 'Government social worker',
    severity: 'medium'
  },

  // === LEGAL PROCEEDINGS ===
  {
    value: 'deposition',
    label: 'Deposition',
    category: 'legal',
    icon: '📜',
    description: 'Legal deposition testimony',
    severity: 'high'
  },
  {
    value: 'court_hearing',
    label: 'Court Hearing',
    category: 'legal',
    icon: '🏛️',
    description: 'Court appearance',
    severity: 'high'
  },
  {
    value: 'attorney_meeting',
    label: 'Attorney Meeting',
    category: 'legal',
    icon: '👔',
    description: 'Meeting with lawyer',
    severity: 'low'
  },
  {
    value: 'mediation',
    label: 'Mediation',
    category: 'legal',
    icon: '🤝',
    description: 'Dispute mediation session',
    severity: 'medium'
  },
  {
    value: 'arbitration',
    label: 'Arbitration',
    category: 'legal',
    icon: '⚖️',
    description: 'Binding arbitration',
    severity: 'high'
  },
  {
    value: 'probation_parole',
    label: 'Probation/Parole Meeting',
    category: 'legal',
    icon: '📅',
    description: 'Probation or parole check-in',
    severity: 'medium'
  },

  // === MEDICAL & HEALTHCARE ===
  {
    value: 'involuntary_hold',
    label: 'Involuntary Hold (5150)',
    category: 'medical',
    icon: '🚑',
    description: 'Psychiatric hold situation',
    severity: 'critical'
  },
  {
    value: 'hospital_dispute',
    label: 'Hospital Dispute',
    category: 'medical',
    icon: '🏥',
    description: 'Disagreement with hospital/staff',
    severity: 'high'
  },
  {
    value: 'insurance_dispute',
    label: 'Insurance Dispute',
    category: 'medical',
    icon: '📄',
    description: 'Health insurance issue',
    severity: 'medium'
  },
  {
    value: 'medical_malpractice',
    label: 'Medical Malpractice',
    category: 'medical',
    icon: '⚕️',
    description: 'Documenting potential malpractice',
    severity: 'high'
  },
  {
    value: 'nursing_home',
    label: 'Nursing Home Issue',
    category: 'medical',
    icon: '👴',
    description: 'Elder care facility concern',
    severity: 'high'
  },
  {
    value: 'mental_health_eval',
    label: 'Mental Health Evaluation',
    category: 'medical',
    icon: '🧠',
    description: 'Psych evaluation or assessment',
    severity: 'high'
  },

  // === EDUCATION ===
  {
    value: 'school_disciplinary',
    label: 'School Disciplinary',
    category: 'education',
    icon: '📚',
    description: 'Disciplinary hearing or meeting',
    severity: 'medium'
  },
  {
    value: 'iep_meeting',
    label: 'IEP Meeting',
    category: 'education',
    icon: '📝',
    description: 'Special education IEP meeting',
    severity: 'medium'
  },
  {
    value: 'suspension_expulsion',
    label: 'Suspension/Expulsion',
    category: 'education',
    icon: '🚫',
    description: 'Suspension or expulsion hearing',
    severity: 'high'
  },
  {
    value: 'campus_security',
    label: 'Campus Security',
    category: 'education',
    icon: '🎓',
    description: 'School/campus police encounter',
    severity: 'high'
  },
  {
    value: 'title_ix',
    label: 'Title IX Investigation',
    category: 'education',
    icon: '⚖️',
    description: 'Title IX related meeting',
    severity: 'high'
  },
  {
    value: 'school_meeting',
    label: 'School Administration',
    category: 'education',
    icon: '🏫',
    description: 'Meeting with principal/admin',
    severity: 'low'
  },

  // === WORKPLACE ===
  {
    value: 'hr_meeting',
    label: 'HR Meeting',
    category: 'workplace',
    icon: '👥',
    description: 'Human resources meeting',
    severity: 'medium'
  },
  {
    value: 'termination_meeting',
    label: 'Termination Meeting',
    category: 'workplace',
    icon: '📤',
    description: 'Being fired or laid off',
    severity: 'high'
  },
  {
    value: 'workplace_investigation',
    label: 'Workplace Investigation',
    category: 'workplace',
    icon: '🔎',
    description: 'Internal investigation',
    severity: 'high'
  },
  {
    value: 'performance_review',
    label: 'Performance Review',
    category: 'workplace',
    icon: '📊',
    description: 'Performance evaluation',
    severity: 'low'
  },
  {
    value: 'union_meeting',
    label: 'Union Meeting',
    category: 'workplace',
    icon: '✊',
    description: 'Union-related meeting',
    severity: 'medium'
  },
  {
    value: 'discrimination_complaint',
    label: 'Discrimination Complaint',
    category: 'workplace',
    icon: '⚠️',
    description: 'Filing or discussing discrimination',
    severity: 'high'
  },
  {
    value: 'osha_inspection',
    label: 'OSHA Inspection',
    category: 'workplace',
    icon: '🦺',
    description: 'Workplace safety inspection',
    severity: 'medium'
  },

  // === HOUSING ===
  {
    value: 'landlord_dispute',
    label: 'Landlord Dispute',
    category: 'housing',
    icon: '🏠',
    description: 'Issue with landlord',
    severity: 'medium'
  },
  {
    value: 'eviction_notice',
    label: 'Eviction Notice',
    category: 'housing',
    icon: '📨',
    description: 'Receiving eviction notice',
    severity: 'high'
  },
  {
    value: 'eviction_proceeding',
    label: 'Eviction Proceeding',
    category: 'housing',
    icon: '⚖️',
    description: 'Eviction court or hearing',
    severity: 'critical'
  },
  {
    value: 'housing_inspection',
    label: 'Housing Inspection',
    category: 'housing',
    icon: '🔍',
    description: 'Housing authority inspection',
    severity: 'medium'
  },
  {
    value: 'section8_inspection',
    label: 'Section 8 Inspection',
    category: 'housing',
    icon: '📋',
    description: 'Section 8/HUD inspection',
    severity: 'medium'
  },
  {
    value: 'illegal_entry',
    label: 'Illegal Entry',
    category: 'housing',
    icon: '🚪',
    description: 'Landlord entering without notice',
    severity: 'high'
  },
  {
    value: 'repair_dispute',
    label: 'Repair Dispute',
    category: 'housing',
    icon: '🔧',
    description: 'Dispute over repairs/conditions',
    severity: 'medium'
  },

  // === ACCIDENTS & INCIDENTS ===
  {
    value: 'car_accident',
    label: 'Car Accident',
    category: 'accidents',
    icon: '🚗',
    description: 'Vehicle collision',
    severity: 'high'
  },
  {
    value: 'slip_fall',
    label: 'Slip and Fall',
    category: 'accidents',
    icon: '⚠️',
    description: 'Injury on property',
    severity: 'high'
  },
  {
    value: 'property_damage',
    label: 'Property Damage',
    category: 'accidents',
    icon: '💥',
    description: 'Damage to your property',
    severity: 'medium'
  },
  {
    value: 'witness_incident',
    label: 'Witness to Incident',
    category: 'accidents',
    icon: '👁️',
    description: 'Documenting as a witness',
    severity: 'medium'
  },
  {
    value: 'assault_battery',
    label: 'Assault / Battery',
    category: 'accidents',
    icon: '🚨',
    description: 'Physical altercation',
    severity: 'critical'
  },
  {
    value: 'theft_robbery',
    label: 'Theft / Robbery',
    category: 'accidents',
    icon: '🔓',
    description: 'Theft or robbery incident',
    severity: 'high'
  },
  {
    value: 'vandalism',
    label: 'Vandalism',
    category: 'accidents',
    icon: '🎨',
    description: 'Property vandalism',
    severity: 'medium'
  },

  // === CONSUMER & BUSINESS ===
  {
    value: 'contract_dispute',
    label: 'Contract Dispute',
    category: 'consumer',
    icon: '📝',
    description: 'Disagreement over contract',
    severity: 'medium'
  },
  {
    value: 'debt_collector',
    label: 'Debt Collector',
    category: 'consumer',
    icon: '📞',
    description: 'Debt collection call/visit',
    severity: 'medium'
  },
  {
    value: 'fraud_scam',
    label: 'Fraud / Scam',
    category: 'consumer',
    icon: '🚫',
    description: 'Documenting fraud or scam',
    severity: 'high'
  },
  {
    value: 'insurance_claim',
    label: 'Insurance Claim',
    category: 'consumer',
    icon: '📄',
    description: 'Filing or disputing claim',
    severity: 'medium'
  },
  {
    value: 'consumer_complaint',
    label: 'Consumer Complaint',
    category: 'consumer',
    icon: '📢',
    description: 'Business/service complaint',
    severity: 'low'
  },
  {
    value: 'repo_attempt',
    label: 'Repossession Attempt',
    category: 'consumer',
    icon: '🚙',
    description: 'Vehicle/property repo',
    severity: 'high'
  },
  {
    value: 'other',
    label: 'Other',
    category: 'consumer',
    icon: '📌',
    description: 'Other encounter type',
    severity: 'medium'
  }
];

// ==================== RIGHTS REMINDERS BY CATEGORY ====================

export const rightsRemindersByCategory = {
  law_enforcement: [
    "You have the right to remain silent.",
    "You do not have to consent to a search.",
    "Ask: 'Am I being detained or am I free to go?'",
    "You have the right to an attorney.",
    "Do not physically resist, even if your rights are violated.",
    "You can refuse to answer questions without a lawyer.",
    "Ask for badge numbers and names.",
    "Everything is being recorded for your protection."
  ],
  
  child_family: [
    "You have the right to know the specific allegations.",
    "You can request to see credentials and a warrant.",
    "You do not have to let CPS in without a warrant.",
    "You can have an attorney present for interviews.",
    "You can record this interaction (check state laws).",
    "Do not sign anything without reading it fully.",
    "Ask for everything in writing.",
    "Stay calm and cooperative but protect your rights."
  ],
  
  government: [
    "Ask to see official credentials and identification.",
    "You have the right to remain silent with immigration.",
    "Do not sign any documents you don't understand.",
    "You can request an interpreter.",
    "Ask for the specific law or regulation being cited.",
    "Request all notices and citations in writing.",
    "You may have the right to refuse entry without a warrant.",
    "Document everything - names, badge numbers, time."
  ],
  
  legal: [
    "Do not speak without your attorney present.",
    "You have the right to review all documents.",
    "Take notes of everything discussed.",
    "Ask for clarification if you don't understand.",
    "You can request breaks if needed.",
    "Do not agree to anything you're unsure about.",
    "Everything you say can be used in court.",
    "Request copies of all signed documents."
  ],
  
  medical: [
    "You have the right to informed consent.",
    "You can refuse treatment (with limited exceptions).",
    "Ask for all treatment options in writing.",
    "You can request a patient advocate.",
    "Document all medications and procedures.",
    "You have the right to your medical records.",
    "You can request a second opinion.",
    "Ask about costs before agreeing to treatment."
  ],
  
  education: [
    "You have the right to see all evidence against your child.",
    "Your child may have a right to an advocate.",
    "Request all policies and procedures in writing.",
    "You can record meetings (notify them first).",
    "Ask for written minutes of all meetings.",
    "Request specific accommodations in writing.",
    "You can appeal most disciplinary decisions.",
    "Know the difference between school and legal rights."
  ],
  
  workplace: [
    "You may have the right to a witness (Weingarten rights).",
    "Do not sign anything under pressure.",
    "Request all accusations in writing.",
    "You can take notes during meetings.",
    "Ask for time to consult with an attorney.",
    "Document everything - dates, times, who said what.",
    "Know your company's grievance procedures.",
    "You may have whistleblower protections."
  ],
  
  housing: [
    "Know your state's landlord entry notice requirements.",
    "You have the right to habitable living conditions.",
    "Document all communications in writing.",
    "Request repairs in writing and keep copies.",
    "You cannot be evicted without proper legal process.",
    "Know your rights regarding security deposits.",
    "Document property conditions with photos/video.",
    "You may have rights to relocation assistance."
  ],
  
  accidents: [
    "Do not admit fault at the scene.",
    "Exchange information with all parties.",
    "Document everything with photos and video.",
    "Get contact info from all witnesses.",
    "Seek medical attention even if you feel fine.",
    "File a police report if applicable.",
    "Do not give recorded statements to insurance.",
    "Contact your insurance company promptly."
  ],
  
  consumer: [
    "Debt collectors must identify themselves.",
    "You can request debt validation in writing.",
    "You have the right to dispute inaccurate information.",
    "Keep records of all communications.",
    "Know the statute of limitations on debts.",
    "You can request they stop calling you.",
    "Do not give out personal financial information.",
    "Report violations to the CFPB or FTC."
  ]
};

// ==================== KEY QUESTIONS BY TYPE ====================

export const keyQuestionsByType = {
  // Law Enforcement
  traffic_stop: [
    "Why was I pulled over?",
    "Am I being detained or am I free to go?",
    "Are you requesting or ordering me to do that?"
  ],
  home_visit_police: [
    "Do you have a warrant?",
    "Can I see the warrant?",
    "What is the purpose of this visit?"
  ],
  arrest: [
    "What am I being charged with?",
    "I want to speak to an attorney.",
    "I am invoking my right to remain silent."
  ],
  
  // CPS
  cps_investigation: [
    "What are the specific allegations?",
    "Do you have a warrant or court order?",
    "Can I have this in writing?"
  ],
  cps_home_visit: [
    "May I see your credentials?",
    "Is this visit court-ordered?",
    "Can I have my attorney present?"
  ],
  
  // Government
  ice_cbp: [
    "Am I free to leave?",
    "I do not consent to a search.",
    "I wish to remain silent."
  ],
  
  // Workplace
  termination_meeting: [
    "Can I have this in writing?",
    "What is the reason for termination?",
    "Can I have time to consult an attorney?"
  ],
  
  // Housing
  eviction_notice: [
    "Is this a legal notice?",
    "What is the reason for eviction?",
    "What are my options to cure this?"
  ],
  
  // Default
  default: [
    "Can you explain what's happening?",
    "Can I have this in writing?",
    "May I consult with someone before proceeding?"
  ]
};

// ==================== RED FLAGS BY CATEGORY ====================

export const redFlagsByCategory = {
  law_enforcement: [
    "Searching without consent or warrant",
    "Not stating the reason for the stop",
    "Threatening arrest for refusing to answer",
    "Excessive force or aggression",
    "Refusing to identify themselves",
    "Not reading Miranda rights during arrest"
  ],
  
  child_family: [
    "Demanding immediate access without warrant",
    "Interviewing child without parent present",
    "Making threats about child removal",
    "Not providing written documentation",
    "Refusing to explain allegations",
    "Pressuring to sign documents immediately"
  ],
  
  government: [
    "No official identification or credentials",
    "Refusing to provide documentation",
    "Demanding immediate payment",
    "Threatening arrest or deportation",
    "Requesting personal financial information",
    "Refusing to explain the legal basis"
  ],
  
  workplace: [
    "Denying your right to a witness",
    "Pressuring you to sign immediately",
    "Recording without your knowledge",
    "Retaliating for complaints",
    "Discriminatory statements",
    "Refusing to provide written documentation"
  ],
  
  housing: [
    "Entering without proper notice",
    "Illegal lockout attempt",
    "Shutting off utilities illegally",
    "Harassment or intimidation",
    "Refusing to make required repairs",
    "Improper eviction procedures"
  ]
};

// ==================== HELPER FUNCTIONS ====================

/**
 * Get encounter type configuration by value
 */
export const getEncounterType = (value) => {
  return universalEncounterTypes.find(t => t.value === value);
};

/**
 * Get encounter types by category
 */
export const getEncounterTypesByCategory = (categoryId) => {
  return universalEncounterTypes.filter(t => t.category === categoryId);
};

/**
 * Get rights reminders for an encounter type
 */
export const getRightsReminders = (encounterValue) => {
  const type = getEncounterType(encounterValue);
  if (!type) return rightsRemindersByCategory.law_enforcement;
  return rightsRemindersByCategory[type.category] || rightsRemindersByCategory.law_enforcement;
};

/**
 * Get key questions for an encounter type
 */
export const getKeyQuestions = (encounterValue) => {
  return keyQuestionsByType[encounterValue] || keyQuestionsByType.default;
};

/**
 * Get red flags for an encounter type
 */
export const getRedFlags = (encounterValue) => {
  const type = getEncounterType(encounterValue);
  if (!type) return redFlagsByCategory.law_enforcement;
  return redFlagsByCategory[type.category] || [];
};

/**
 * Get category info
 */
export const getCategory = (categoryId) => {
  return encounterCategories.find(c => c.id === categoryId);
};

/**
 * Get severity color class
 */
export const getSeverityColor = (severity) => {
  switch (severity) {
    case 'critical': return 'text-red-500 bg-red-500/10 border-red-500/30';
    case 'high': return 'text-orange-500 bg-orange-500/10 border-orange-500/30';
    case 'medium': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30';
    case 'low': return 'text-green-500 bg-green-500/10 border-green-500/30';
    default: return 'text-gray-500 bg-gray-500/10 border-gray-500/30';
  }
};

export default universalEncounterTypes;
