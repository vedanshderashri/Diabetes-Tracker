/**
 * DiaCare AI — Advanced Medical Logic Engine
 * Includes Chat Dialogue Manager, OCR Scan Simulator, Risk Prediction and Daily Planner
 */

// Global State
const patientProfile = {
  gender: 'Female',
  age: 45,
  hypertension: 0,
  heartDisease: 0,
  smokingHistory: 'never',
  bmi: 24.5,
  hba1c: 5.5,
  glucose: 110,
  symptoms: {},
  treatmentPreference: 'Integrated',
  dietType: 'Indian Veg (Budget-Friendly)', // Default
};

// State Machine for Chat Flow
let chatState = 'GREETING'; // GREETING, SELECT_INPUT_METHOD, COLLECTING_SYMPTOMS, SELECT_TREATMENT, CONVERSATIONAL
let currentSymptomIndex = 0;
const symptomQuestions = [
  { key: 'gender', label: 'Gender', text: 'To start, what is your gender?', type: 'select', options: ['Female', 'Male'] },
  { key: 'age', label: 'Age', text: 'How old are you?', type: 'number', min: 1, max: 115 },
  { key: 'frequent_urination', label: 'Frequent Urination', text: 'Do you experience unusually frequent urination, especially during the night?', type: 'yesno' },
  { key: 'excessive_thirst', label: 'Excessive Thirst', text: 'Do you feel excessively thirsty or dehydrated, even after drinking plenty of water?', type: 'yesno' },
  { key: 'weight_loss', label: 'Sudden Weight Loss', text: 'Have you noticed sudden, unexplained weight loss recently?', type: 'yesno' },
  { key: 'fatigue', label: 'Fatigue', text: 'Do you suffer from persistent fatigue, weakness, or lethargy?', type: 'yesno' },
  { key: 'slow_healing', label: 'Slow Wound Healing', text: 'Do you notice that cuts, bruises, or sores take an unusually long time to heal?', type: 'yesno' },
  { key: 'tingling', label: 'Tingling in Extremities', text: 'Do you feel frequent tingling, numbness, or a pins-and-needles sensation in your hands or feet?', type: 'yesno' },
  { key: 'family_history', label: 'Family History', text: 'Is there a history of diabetes in your immediate family (parents or siblings)?', type: 'yesno' },
  { key: 'hypertension', label: 'Hypertension', text: 'Have you ever been diagnosed with high blood pressure (Hypertension)?', type: 'yesno' },
  { key: 'heart_disease', label: 'Heart Disease', text: 'Do you have any history of coronary heart disease or other heart conditions?', type: 'yesno' },
  { key: 'bmi_group', label: 'Weight Category', text: 'How would you describe your current body mass index or weight state?', type: 'select', options: ['Underweight', 'Normal Weight', 'Overweight', 'Obese'] }
];

// Q&A Database for diabetes questions
const qaDatabase = [
  {
    keywords: ['metformin', 'glucophage', 'medicine', 'side effect'],
    answer: `<strong>Metformin Guidance:</strong> Metformin (Glucophage) is the most commonly prescribed first-line oral medication for Type 2 Diabetes. It acts by reducing glucose production in the liver and improving insulin sensitivity in muscles.<br><br>
    <strong>Common Side Effects:</strong> Nausea, mild stomach upset, abdominal bloating, diarrhea. These are usually temporary and improve when taken with meals.<br><br>
    <em>Safety Disclaimer: Dosage must be determined by a certified physician. Never modify or discontinue your prescribed medication schedule on your own.</em>`
  },
  {
    keywords: ['insulin', 'injection', 'basal', 'bolus'],
    answer: `<strong>Insulin Therapy Basics:</strong> Insulin is crucial for managing Type 1 Diabetes and frequently necessary in advanced Type 2 Diabetes.<br><br>
    - <strong>Basal Insulin:</strong> Long-acting insulin that keeps blood sugar steady overnight and between meals.<br>
    - <strong>Bolus Insulin:</strong> Rapid or short-acting insulin injected before meals to manage post-meal glucose spikes.<br><br>
    <em>Important Safety: Exact units depend on carbohydrate counts and clinical charts. Never inject insulin without a clear, doctor-approved dosage schedule.</em>`
  },
  {
    keywords: ['hba1c', 'average sugar', 'three months'],
    answer: `<strong>HbA1c (Hemoglobin A1c) Explained:</strong> HbA1c measures the percentage of your red blood cells that have sugar coated on them, reflecting your average blood glucose levels over the past 2 to 3 months.<br><br>
    - <strong>Normal:</strong> Below 5.7%<br>
    - <strong>Prediabetes:</strong> 5.7% to 6.4% (indicates lifestyle actions are needed)<br>
    - <strong>Diabetes:</strong> 6.5% or higher (confirmed by dual testing)`
  },
  {
    keywords: ['low sugar', 'hypoglycemia', 'shaking', 'sweating'],
    answer: `<strong>Hypoglycemia (Low Blood Sugar - below 70 mg/dL):</strong> This is a medical emergency that triggers trembling, sweating, racing heart, and confusion.<br><br>
    <strong>Immediate action (The 15-15 Rule):</strong><br>
    1. Consume 15 grams of fast-acting sugar (e.g., 4 ounces of fruit juice, 3-4 glucose tablets, or 1 tablespoon of sugar/honey).<br>
    2. Wait 15 minutes, then check blood sugar.<br>
    3. If still below 70 mg/dL, repeat the process. If symptoms worsen, seek immediate emergency clinic support.`
  },
  {
    keywords: ['ayurveda', 'herbs', 'methi', 'karela'],
    answer: `<strong>Ayurvedic Diabetes Support (Madhumeha):</strong> Ayurveda focuses on lifestyle moderation (Ahar & Vihar) and natural herbs:<br><br>
    - <strong>Methi (Fenugreek seeds):</strong> Helps slow carbohydrate absorption.<br>
    - <strong>Karela (Bitter Melon):</strong> Contains polypeptide-p, which mimics insulin.<br>
    - <strong>Jamun Seed Powder:</strong> Helps prevent starch from converting into sugar.<br><br>
    <em>Note: Traditional wellness supports lifestyle management but must be monitored. Consult a certified Ayurvedic physician (BAMS) for personal formulations.</em>`
  }
];

// Comparison chart reference
let progressChart = null;

// Initialize Web App
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  initChat();
  setupForms();
  setupReportScanner();
  setupCompareTracker();
  updateRiskEngine(); // Set initial state
});

// 1. Navigation Panel Switcher
function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const panels = document.querySelectorAll('.workspace-panel');

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      // Remove active states
      navItems.forEach(nav => nav.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      // Add active state to selected item
      item.classList.add('active');
      const targetPanelId = item.getAttribute('data-panel');
      document.getElementById(targetPanelId).classList.add('active');
      
      // If switching to Compare, trigger canvas redrawing
      if (targetPanelId === 'panel-comparison' && progressChart) {
        progressChart.update();
      }
    });
  });
}

// 2. Chat Assistant Engine
const chatFeed = document.getElementById('chat-feed');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');

function initChat() {
  // Clear feed
  chatFeed.innerHTML = '';
  
  // Inject greeting
  appendBotMessage(
    `Hello, I’m <strong>DiaCare AI</strong> — your advanced diabetes risk analysis, lifestyle guidance, and prescription assistant.<br><br>
    I can analyze symptoms, parse laboratory medical reports, and offer highly customized Ayurvedic, Homeopathic, Allopathic, or Integrated care plans.<br><br>
    <em>Important Safety Note: I am a clinical sandbox simulation and do not replace certified doctor reviews. In case of high danger signs (chest pain, shortness of breath, confusion), please contact medical emergency teams instantly.</em>`
  );
  
  showInputMethodSelector();
}

function showInputMethodSelector() {
  chatState = 'SELECT_INPUT_METHOD';
  
  appendBotMessage("How would you like to check your diabetes risk today?");
  
  const optionsContainer = document.createElement('div');
  optionsContainer.className = 'quick-replies';
  
  const options = [
    { text: '1. Enter Symptoms Conversationally', action: 'symptoms' },
    { text: '2. Upload Medical Report (OCR)', action: 'report' },
    { text: '3. Enter Lab Values Manually', action: 'manual' }
  ];
  
  options.forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'quick-reply-btn';
    btn.innerHTML = opt.text;
    btn.addEventListener('click', () => {
      appendUserMessage(opt.text);
      optionsContainer.remove();
      handleInputMethodChoice(opt.action);
    });
    optionsContainer.appendChild(btn);
  });
  
  chatFeed.appendChild(optionsContainer);
  scrollToBottom();
}

function handleInputMethodChoice(choice) {
  if (choice === 'symptoms') {
    chatState = 'COLLECTING_SYMPTOMS';
    currentSymptomIndex = 0;
    patientProfile.symptoms = {};
    askNextSymptom();
  } else if (choice === 'report') {
    appendBotMessage("Excellent choice. I have activated the <strong>Medical Report Scanner</strong> tab on the sidebar. Please click it, upload your lab PDF/Image, and confirm the extracted values.");
    triggerSidebarNavigation('panel-scanner');
  } else if (choice === 'manual') {
    appendBotMessage("Understood. I have loaded the <strong>Quick Risk Calculator</strong> tab. Please enter your latest blood values, and I will instantly process your clinical score.");
    triggerSidebarNavigation('panel-manual-check');
  }
}

function askNextSymptom() {
  if (currentSymptomIndex < symptomQuestions.length) {
    const question = symptomQuestions[currentSymptomIndex];
    appendBotMessage(question.text);
    
    // Render appropriate inputs
    if (question.type === 'yesno') {
      const container = document.createElement('div');
      container.className = 'quick-replies';
      
      const yesBtn = document.createElement('button');
      yesBtn.className = 'quick-reply-btn';
      yesBtn.innerText = 'Yes';
      yesBtn.addEventListener('click', () => {
        appendUserMessage('Yes');
        container.remove();
        saveSymptomValue(question.key, 1);
      });
      
      const noBtn = document.createElement('button');
      noBtn.className = 'quick-reply-btn';
      noBtn.innerText = 'No';
      noBtn.addEventListener('click', () => {
        appendUserMessage('No');
        container.remove();
        saveSymptomValue(question.key, 0);
      });
      
      container.appendChild(yesBtn);
      container.appendChild(noBtn);
      chatFeed.appendChild(container);
      scrollToBottom();
    } else if (question.type === 'select') {
      const container = document.createElement('div');
      container.className = 'quick-replies';
      
      question.options.forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'quick-reply-btn';
        btn.innerText = opt;
        btn.addEventListener('click', () => {
          appendUserMessage(opt);
          container.remove();
          saveSymptomValue(question.key, opt);
        });
        container.appendChild(btn);
      });
      chatFeed.appendChild(container);
      scrollToBottom();
    } else if (question.type === 'number') {
      userInput.placeholder = `Enter number for ${question.label}...`;
    }
  } else {
    // All symptoms collected!
    chatState = 'SELECT_TREATMENT';
    askTreatmentPreference();
  }
}

function saveSymptomValue(key, value) {
  patientProfile.symptoms[key] = value;
  
  // Sync core profile variables
  if (key === 'gender') patientProfile.gender = value;
  if (key === 'age') patientProfile.age = parseInt(value) || 30;
  if (key === 'hypertension') patientProfile.hypertension = value;
  if (key === 'heart_disease') patientProfile.heartDisease = value;
  if (key === 'bmi_group') {
    if (value === 'Underweight') patientProfile.bmi = 17.5;
    else if (value === 'Normal Weight') patientProfile.bmi = 22.0;
    else if (value === 'Overweight') patientProfile.bmi = 27.5;
    else if (value === 'Obese') patientProfile.bmi = 34.5;
  }
  
  currentSymptomIndex++;
  userInput.placeholder = "Type symptoms or ask a diabetes question...";
  
  // Update clinical calculator fields to sync values in background
  syncProfileToCalculatorForm();
  updateRiskEngine();
  
  setTimeout(askNextSymptom, 400);
}

function askTreatmentPreference() {
  appendBotMessage("Which treatment style or guidance mode would you prefer to review for your daily planner?<br><em>Select an approach below:</em>");
  
  const container = document.createElement('div');
  container.className = 'quick-replies';
  
  const modes = [
    { text: 'Allopathy (Modern Western Medicine)', val: 'Allopathy' },
    { text: 'Ayurveda (Traditional Herbs & Yoga)', val: 'Ayurveda' },
    { text: 'Homeopathy (Gentle Individual Care)', val: 'Homeopathy' },
    { text: 'Integrated Approach (Combined Balance)', val: 'Integrated' }
  ];
  
  modes.forEach(mode => {
    const btn = document.createElement('button');
    btn.className = 'quick-reply-btn';
    btn.innerText = mode.text;
    btn.addEventListener('click', () => {
      appendUserMessage(mode.text);
      container.remove();
      patientProfile.treatmentPreference = mode.val;
      generateClinicalSummary();
    });
    container.appendChild(btn);
  });
  
  chatFeed.appendChild(container);
  scrollToBottom();
}

function generateClinicalSummary() {
  chatState = 'CONVERSATIONAL';
  
  const riskResult = calculateDiabetesRiskScore();
  const treatment = patientProfile.treatmentPreference;
  
  let summaryText = `<h3>Health Analysis & Diagnosis Report</h3>
  <strong>Symptom Risk Level:</strong> <span style="color:${riskResult.color}; font-weight:bold;">${riskResult.level} (${riskResult.score}%)</span><br>
  <strong>Estimated Classification:</strong> <strong>${riskResult.classification}</strong><br><br>
  <strong>Key Findings:</strong><br>`;
  
  const factors = getRiskFactors();
  factors.forEach(f => {
    summaryText += `• ${f}<br>`;
  });
  
  summaryText += `<br><strong>Suggested Clinical Next Steps:</strong><br>
  1. Schedule a formal lab draw for HbA1c and Fasting Plasma Glucose (FPG) with a local clinic.<br>
  2. Maintain a daily capillary blood sugar monitoring log.<br>
  3. Bring emergency symptoms to medical attention instantly.<br><br>
  <strong>${treatment.toUpperCase()} WELLNESS PLAN:</strong><br>`;
  
  if (treatment === 'Allopathy') {
    summaryText += `• **Medications:** Standard clinical guidelines frequently incorporate oral agents (such as Metformin) to raise insulin cell response. <em>Consult a physician before initiating treatment.</em><br>
    • **Capillary Log:** Test fasting glucose levels 3 times weekly using a home glucometer.<br>
    • **Diet Control:** Strictly restrict processed simple carbohydrates and sweet beverages.<br>
    • **Exercise:** Complete 150 minutes of moderate aerobic workouts weekly.`;
  } else if (treatment === 'Ayurveda') {
    summaryText += `• **Herbal Support:** Incorporate standardized herbal aids under supervision (e.g., Fenugreek/Methi seeds daily, Bitter Melon/Karela juice, or Jamun powder).<br>
    • **Yogic Practice:** Practice stress mitigation through Pranayama (deep breathing) and Mandukasana (frog pose) daily.<br>
    • **Dietary Ahar:** Emphasize bitter, astringent, and high-fiber foods.<br>
    • **Routine (Dinacharya):** Avoid day sleeping and maintain structured wake/sleep hours.`;
  } else if (treatment === 'Homeopathy') {
    summaryText += `• **Gentle Remedies:** Consultation is key to prescribe individual remedies based on mental state, food desires, and thirst indicators.<br>
    • **Wellness Focus:** Integrate walking programs and natural sleep scheduling.<br>
    • **Precautions:** Avoid strong stimulants (coffee, menthol) near drug intake times.`;
  } else { // Integrated
    summaryText += `• **Dual Integration:** Rely on modern testing tools while employing natural lifestyle aids for optimal glycemic balance.<br>
    • **Medical Shield:** Keep regular Metformin or doctor prescriptions active while using Methi or Yoga to support management.<br>
    • **Lifestyle:** Exercise 30 minutes daily and keep hydration levels high.`;
  }
  
  summaryText += `<br><br>I have generated a customized <strong>Interactive Lifestyle and Diet Planner</strong> in your right-hand sidebar. Try ticking off the daily items as you complete them!`;
  
  appendBotMessage(summaryText);
  
  // Re-generate the planner checklist
  generateInteractivePlannerChecklist();
  
  // Keep chatbot profile synced
  updateRiskEngine();
}

// Q&A text response handler
chatForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = userInput.value.trim();
  if (!text) return;
  
  // Clear input
  userInput.value = '';
  appendUserMessage(text);
  
  // Process State
  if (chatState === 'COLLECTING_SYMPTOMS') {
    const question = symptomQuestions[currentSymptomIndex];
    if (question.type === 'number') {
      const num = parseInt(text);
      if (isNaN(num) || num < question.min || num > question.max) {
        appendBotMessage(`Please enter a valid number for ${question.label} (${question.min} - ${question.max}).`);
      } else {
        saveSymptomValue(question.key, num);
      }
    } else {
      appendBotMessage("Please use the interactive buttons to answer this question.");
    }
    return;
  }
  
  // Normal Q&A processing
  showTypingIndicator();
  setTimeout(() => {
    removeTypingIndicator();
    processGeneralChatInput(text);
  }, 600);
});

function processGeneralChatInput(input) {
  const textLower = input.toLowerCase();
  
  // Check for dangerous emergency signs in input text
  const emergencyKeywords = ['chest pain', 'unconscious', 'severe dizziness', 'difficulty breathing', 'breathlessness', 'foot infection', 'coma', 'fainted'];
  const hasEmergency = emergencyKeywords.some(keyword => textLower.includes(keyword));
  
  if (hasEmergency) {
    triggerEmergencyBanner("Extreme high-risk indicator detected (e.g. chest pain, breathing issues). This requires immediate emergency clinical support. Please call ambulance or head to the nearest clinic!");
    appendBotMessage(`<strong>CRITICAL WARNING:</strong> Your symptoms represent potential severe complications. <span style="color:var(--critical-crimson); font-weight:bold;">Please seek immediate medical attention or consult a certified emergency doctor.</span>`);
    return;
  }

  // Check for dietary choices or profile variables in conversation
  if (textLower.includes('vegetarian') || textLower.includes('non-vegetarian') || textLower.includes('budget') || textLower.includes('indian')) {
    if (textLower.includes('non-veg')) {
      patientProfile.dietType = 'Non-Vegetarian (Premium)';
      appendBotMessage("Diet preference updated to **Non-Vegetarian**. I will tailor your planner to include low-carb lean meats like grilled fish and chicken breast.");
    } else if (textLower.includes('veg')) {
      patientProfile.dietType = 'Indian Veg (Budget-Friendly)';
      appendBotMessage("Diet preference updated to **Indian Vegetarian**. I will tailor your planner to include lentils, chickpeas, paneer, and local leafy vegetables.");
    }
    generateInteractivePlannerChecklist();
    return;
  }

  // Check Q&A Database matches
  let matchedResponse = null;
  for (const qa of qaDatabase) {
    const match = qa.keywords.some(keyword => textLower.includes(keyword));
    if (match) {
      matchedResponse = qa.answer;
      break;
    }
  }
  
  if (matchedResponse) {
    appendBotMessage(matchedResponse);
  } else {
    // Default reply
    appendBotMessage(`Thank you for your question. Based on DiaCare AI guidelines, managing diabetes effectively requires regular blood sugar tracking, eating low glycemic foods, and remaining active.<br><br>
    Try asking about: <em>Metformin side effects, HbA1c explanation, Hypoglycemia treatment, or Ayurvedic herbs.</em>`);
  }
}

// Helpers for Chat bubbles
function appendBotMessage(content) {
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble bot';
  bubble.innerHTML = `
    <div class="bubble-content">${content}</div>
    <div class="bubble-meta">DiaCare AI • ${getFormattedTime()}</div>
  `;
  chatFeed.appendChild(bubble);
  scrollToBottom();
}

function appendUserMessage(content) {
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble user';
  bubble.innerHTML = `
    <div class="bubble-content">${content}</div>
    <div class="bubble-meta">You • ${getFormattedTime()}</div>
  `;
  chatFeed.appendChild(bubble);
  scrollToBottom();
}

function showTypingIndicator() {
  const indicator = document.createElement('div');
  indicator.className = 'chat-bubble bot typing-indicator';
  indicator.id = 'chat-typing-indicator';
  indicator.innerHTML = `
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
  `;
  chatFeed.appendChild(indicator);
  scrollToBottom();
}

function removeTypingIndicator() {
  const indicator = document.getElementById('chat-typing-indicator');
  if (indicator) indicator.remove();
}

function scrollToBottom() {
  chatFeed.scrollTop = chatFeed.scrollHeight;
}

function getFormattedTime() {
  const now = new Date();
  return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function triggerSidebarNavigation(panelId) {
  const navItem = document.querySelector(`.nav-item[data-panel="${panelId}"]`);
  if (navItem) navItem.click();
}

// 3. Clinical Calculator Form Logic
function setupForms() {
  const manualForm = document.getElementById('manual-risk-form');
  const resetBtn = document.getElementById('reset-manual-btn');
  const bmiInput = document.getElementById('calc-bmi');
  const bmiDisplay = document.getElementById('bmi-display');

  // BMI helper descriptor
  bmiInput.addEventListener('input', () => {
    const val = parseFloat(bmiInput.value);
    if (!val) { bmiDisplay.innerText = ''; return; }
    if (val < 18.5) bmiDisplay.innerText = '(Underweight)';
    else if (val < 25) bmiDisplay.innerText = '(Normal)';
    else if (val < 30) bmiDisplay.innerText = '(Overweight)';
    else bmiDisplay.innerText = '(Obese)';
  });

  manualForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    // Save to global profile
    patientProfile.gender = document.getElementById('calc-gender').value;
    patientProfile.age = parseInt(document.getElementById('calc-age').value);
    patientProfile.hypertension = parseInt(document.getElementById('calc-hypertension').value);
    patientProfile.heartDisease = parseInt(document.getElementById('calc-heart').value);
    patientProfile.smokingHistory = document.getElementById('calc-smoking').value;
    patientProfile.bmi = parseFloat(bmiInput.value);
    patientProfile.hba1c = parseFloat(document.getElementById('calc-hba1c').value);
    patientProfile.glucose = parseInt(document.getElementById('calc-glucose').value);
    
    // Sync symptoms list loosely
    patientProfile.symptoms = {
      family_history: 0,
      frequent_urination: patientProfile.glucose > 160 ? 1 : 0,
      excessive_thirst: patientProfile.glucose > 180 ? 1 : 0
    };

    updateRiskEngine();
    
    // Switch back to chat to present treatment choice
    appendBotMessage(`<h3>Manual Clinical Entry Success</h3>
    I have received your direct biological parameters and loaded them into your health card. Let's select your treatment routine preference to finalize your planner.`);
    triggerSidebarNavigation('panel-chatbot');
    chatState = 'SELECT_TREATMENT';
    askTreatmentPreference();
  });

  resetBtn.addEventListener('click', () => {
    manualForm.reset();
    bmiDisplay.innerText = '';
  });
}

function syncProfileToCalculatorForm() {
  document.getElementById('calc-gender').value = patientProfile.gender;
  document.getElementById('calc-age').value = patientProfile.age;
  document.getElementById('calc-hypertension').value = patientProfile.hypertension;
  document.getElementById('calc-heart').value = patientProfile.heartDisease;
  document.getElementById('calc-smoking').value = patientProfile.smokingHistory;
  document.getElementById('calc-bmi').value = patientProfile.bmi;
}

// 4. Report Scanner Logic
function setupReportScanner() {
  const dragZone = document.getElementById('drag-drop-zone');
  const fileInput = document.getElementById('report-file-input');
  const ocrLoader = document.getElementById('ocr-loader');
  const resultsCard = document.getElementById('extracted-results-card');
  const confirmBtn = document.getElementById('confirm-scan-btn');
  const cancelBtn = document.getElementById('cancel-scan-btn');
  const progressText = document.getElementById('scanner-progress-text');

  // Drag operations
  dragZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dragZone.classList.add('dragover');
  });
  dragZone.addEventListener('dragleave', () => {
    dragZone.classList.remove('dragover');
  });
  dragZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dragZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      processMockOCRScan(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      processMockOCRScan(fileInput.files[0]);
    }
  });

  confirmBtn.addEventListener('click', () => {
    // Parse values from form
    patientProfile.glucose = parseInt(document.getElementById('scan-fbs').value) || 120;
    patientProfile.hba1c = parseFloat(document.getElementById('scan-hba1c').value) || 6.0;
    
    // Additional parameters to simulate
    const sbp = parseInt(document.getElementById('scan-sbp').value) || 120;
    patientProfile.hypertension = sbp >= 140 ? 1 : 0;
    
    // Hide card, reset zone
    resultsCard.style.display = 'none';
    dragZone.style.display = 'flex';
    
    updateRiskEngine();
    syncProfileToCalculatorForm();

    appendBotMessage(`<h3>Medical Report Parsed</h3>
    I have processed your uploaded medical report. Extracted values loaded: <br>
    - **Fasting Glucose:** ${patientProfile.glucose} mg/dL<br>
    - **HbA1c Level:** ${patientProfile.hba1c}%<br><br>
    Let's select your wellness treatment mode to customize your checklist.`);
    
    triggerSidebarNavigation('panel-chatbot');
    chatState = 'SELECT_TREATMENT';
    askTreatmentPreference();
  });

  cancelBtn.addEventListener('click', () => {
    resultsCard.style.display = 'none';
    dragZone.style.display = 'flex';
  });

  function processMockOCRScan(file) {
    dragZone.style.display = 'none';
    ocrLoader.style.display = 'flex';
    
    const steps = [
      "Reading uploaded file headers...",
      "Analyzing layout structures and tables...",
      "Performing character segmentation on laboratory bounds...",
      "Extracting HbA1c and plasma glucose records...",
      "OCR scanning complete!"
    ];

    let i = 0;
    const interval = setInterval(() => {
      if (i < steps.length) {
        progressText.innerHTML = steps[i];
        i++;
      } else {
        clearInterval(interval);
        ocrLoader.style.display = 'none';
        
        // Pick simulated values based on name slightly, or standard defaults
        if (file.name.toLowerCase().includes('normal')) {
          document.getElementById('scan-fbs').value = 92;
          document.getElementById('scan-hba1c').value = 5.2;
          document.getElementById('scan-ppbs').value = 125;
          document.getElementById('scan-chol').value = 175;
          document.getElementById('scan-sbp').value = 115;
          document.getElementById('scan-dbp').value = 75;
        } else { // default diabetic report simulation
          document.getElementById('scan-fbs').value = 142;
          document.getElementById('scan-hba1c').value = 7.1;
          document.getElementById('scan-ppbs').value = 210;
          document.getElementById('scan-chol').value = 240;
          document.getElementById('scan-sbp').value = 138;
          document.getElementById('scan-dbp').value = 88;
        }
        
        resultsCard.style.display = 'block';
      }
    }, 600);
  }
}

// 5. Statistics Prediction Engine
// 5. Statistics Prediction Engine (Trained ML Model - L2-Regularized Logistic Regression)
// Trained on 100,000 patient records (diabetes_prediction_dataset.csv)
// Accuracy: 86.24%, Sensitivity (Recall): 89.64%

const modelMeans = {
  age: 41.915006,
  bmi: 27.329349,
  hba1c: 5.529029,
  glucose: 137.938775
};

const modelStds = {
  age: 22.535738,
  bmi: 6.638682,
  hba1c: 1.070192,
  glucose: 40.692685
};

const modelWeights = {
  age: 0.82108401,
  bmi: 0.48613030,
  hba1c: 1.37638173,
  glucose: 0.98119859,
  hypertension: 0.24213663,
  heart_disease: 0.16865328,
  gender_male: -0.21413155,
  gender_other: -0.00070924,
  smoke_current: -0.08020452,
  smoke_former: 0.00206318,
  smoke_ever: -0.03066105,
  smoke_not_current: -0.09127787,
  smoke_never: -0.27204480
};

const modelIntercept = -1.43593183;

function calculateDiabetesRiskScore() {
  // Standardize continuous values
  const stdAge = (patientProfile.age - modelMeans.age) / modelStds.age;
  const stdBmi = (patientProfile.bmi - modelMeans.bmi) / modelStds.bmi;
  const stdHba1c = (patientProfile.hba1c - modelMeans.hba1c) / modelStds.hba1c;
  const stdGlucose = (patientProfile.glucose - modelMeans.glucose) / modelStds.glucose;

  // Encode categorical values
  const genderMale = patientProfile.gender === 'Male' ? 1.0 : 0.0;
  const genderOther = patientProfile.gender === 'Other' ? 1.0 : 0.0;

  const smokeCurrent = patientProfile.smokingHistory === 'current' ? 1.0 : 0.0;
  const smokeFormer = patientProfile.smokingHistory === 'former' ? 1.0 : 0.0;
  const smokeEver = patientProfile.smokingHistory === 'ever' ? 1.0 : 0.0;
  const smokeNotCurrent = patientProfile.smokingHistory === 'not current' ? 1.0 : 0.0;
  const smokeNever = patientProfile.smokingHistory === 'never' ? 1.0 : 0.0;

  // Calculate linear combination
  let z = modelIntercept;
  z += stdAge * modelWeights.age;
  z += stdBmi * modelWeights.bmi;
  z += stdHba1c * modelWeights.hba1c;
  z += stdGlucose * modelWeights.glucose;
  z += (patientProfile.hypertension || 0) * modelWeights.hypertension;
  z += (patientProfile.heartDisease || 0) * modelWeights.heart_disease;
  z += genderMale * modelWeights.gender_male;
  z += genderOther * modelWeights.gender_other;
  z += smokeCurrent * modelWeights.smoke_current;
  z += smokeFormer * modelWeights.smoke_former;
  z += smokeEver * modelWeights.smoke_ever;
  z += smokeNotCurrent * modelWeights.smoke_not_current;
  z += smokeNever * modelWeights.smoke_never;

  // Sigmoid activation to get probability
  const p = 1.0 / (1.0 + Math.exp(-z));
  
  // Convert probability to scale score [1, 99]
  let score = Math.round(p * 100);
  score = Math.min(score, 99);
  score = Math.max(score, 1);
  
  // Level & classification mapping
  let level = 'Low';
  let color = '#10b981';
  let classification = 'Non-diabetic';
  
  if (score >= 60) {
    level = 'High';
    color = '#ef4444';
    
    // Differentiate Type 1 vs Type 2 vs Gestational
    if (patientProfile.age < 30 && patientProfile.bmi < 24) {
      classification = 'Type 1 Diabetes';
    } else if (patientProfile.gender === 'Female' && patientProfile.age >= 20 && patientProfile.age <= 38 && patientProfile.symptoms.gestational === 1) {
      classification = 'Gestational Diabetes';
    } else {
      classification = 'Type 2 Diabetes';
    }
    
    if (patientProfile.glucose >= 250 || patientProfile.hba1c >= 9.0) {
      classification = 'High-risk diabetic condition';
    }
  } else if (score >= 25) {
    level = 'Moderate';
    color = '#f59e0b';
    classification = 'Prediabetes';
  }

  return { score, level, color, classification };
}

function getRiskFactors() {
  const factors = [];
  if (patientProfile.age >= 45) factors.push(`Age factor (${patientProfile.age} yrs)`);
  if (patientProfile.hypertension === 1) factors.push("Clinical Hypertension history");
  if (patientProfile.heartDisease === 1) factors.push("Cardiovascular complications");
  if (patientProfile.bmi >= 25) factors.push(`Elevated body mass (BMI: ${patientProfile.bmi})`);
  if (patientProfile.hba1c >= 5.7) factors.push(`Elevated long-term HbA1c (${patientProfile.hba1c}%)`);
  if (patientProfile.glucose >= 100) factors.push(`Elevated blood glucose levels (${patientProfile.glucose} mg/dL)`);
  if (patientProfile.smokingHistory === 'current') factors.push("Active tobacco consumption");
  
  return factors.length > 0 ? factors : ["No major clinical risk factors identified"];
}

function updateRiskEngine() {
  const result = calculateDiabetesRiskScore();
  
  // 1. Update Gauge labels
  document.getElementById('risk-percent-label').innerText = `${result.score}%`;
  
  const badge = document.getElementById('risk-condition-badge');
  badge.innerText = result.classification;
  badge.className = `risk-badge ${result.level.toLowerCase()}`;
  
  // 2. Animate Circular Gauge
  const circle = document.getElementById('risk-gauge-fill');
  const circumference = 377; // 2 * pi * 60 approx
  const offset = circumference - (circumference * result.score) / 100;
  circle.style.strokeDashoffset = offset;
  
  // 3. Update Risk factors list in sidebar
  const list = document.getElementById('risk-factors-list');
  list.innerHTML = '';
  const factors = getRiskFactors();
  factors.forEach(f => {
    const li = document.createElement('li');
    li.style.listStyleType = 'circle';
    li.style.color = 'var(--text-primary)';
    li.innerText = f;
    list.appendChild(li);
  });

  // 4. Update guest profile card in sidebar
  document.getElementById('profile-name').innerText = `Patient (Age ${patientProfile.age})`;
  document.getElementById('profile-details').innerText = `${result.classification} (${result.level} Risk)`;

  // 5. Check clinical danger thresholds
  if (patientProfile.glucose >= 250 || patientProfile.hba1c >= 9.0) {
    triggerEmergencyBanner(`Critical Lab Alert: Fasting/Random Blood Sugar is extremely high (${patientProfile.glucose} mg/dL) or HbA1c is severely elevated (${patientProfile.hba1c}%). Please seek immediate clinical emergency care.`);
  } else {
    hideEmergencyBanner();
  }
}

// Emergency banner controls
function triggerEmergencyBanner(text) {
  const banner = document.getElementById('emergency-card');
  const desc = document.getElementById('emergency-text');
  desc.innerHTML = text;
  banner.style.display = 'flex';
}

function hideEmergencyBanner() {
  const banner = document.getElementById('emergency-card');
  banner.style.display = 'none';
}

// 6. Interactive Daily Planner
function generateInteractivePlannerChecklist() {
  const checklist = document.getElementById('checklist-widget-feed');
  checklist.innerHTML = '';
  
  const preference = patientProfile.treatmentPreference;
  const diet = patientProfile.dietType;
  
  const routine = [];
  
  // Base daily items
  routine.push({ time: '06:30 AM', task: 'Wake up & drink 500ml warm copper-charged water' });
  
  if (preference === 'Ayurveda') {
    routine.push({ time: '06:45 AM', task: 'Consume pre-soaked Fenugreek (Methi) seeds or Bitter Melon juice' });
    routine.push({ time: '07:00 AM', task: 'Yoga Routine: 15 mins Pranayama + Mandukasana' });
  } else {
    routine.push({ time: '07:00 AM', task: 'Brisk walk: 30 minutes light aerobic routine' });
  }
  
  // Diet specific breakfast
  if (diet.includes('Indian Veg')) {
    routine.push({ time: '08:30 AM', task: 'Breakfast: Steamed oats idli or ragi dosa with green chutney' });
  } else {
    routine.push({ time: '08:30 AM', task: 'Breakfast: Vegetable egg-white omelet with 1 slice whole-wheat toast' });
  }
  
  if (preference === 'Allopathy') {
    routine.push({ time: '08:45 AM', task: 'Administer Metformin (500mg) with/after breakfast as advised' });
  }
  
  routine.push({ time: '11:30 AM', task: 'Hydration check: drink 400ml water + handful of almonds/walnuts' });
  
  // Lunch
  if (diet.includes('Indian Veg')) {
    routine.push({ time: '01:30 PM', task: 'Lunch: 1 cup brown rice or whole-wheat chapati + rich dal + leafy greens' });
  } else {
    routine.push({ time: '01:30 PM', task: 'Lunch: Grilled chicken breast/fish salad with cucumber and spinach' });
  }
  
  routine.push({ time: '05:30 PM', task: 'Evening: Light green tea + baked chana (chickpeas)' });
  
  // Monitoring routine
  if (patientProfile.glucose > 140) {
    routine.push({ time: '07:30 PM', task: 'Measure post-meal blood sugar using capillary glucometer' });
  }
  
  routine.push({ time: '08:30 PM', task: 'Dinner: Light vegetable soup or low-fat paneer paneer/tofu bowl' });
  routine.push({ time: '10:30 PM', task: 'Sleep schedule: complete 7.5 hours of dark-room sleep' });

  // Render routine to UI checklist
  routine.forEach(item => {
    const box = document.createElement('div');
    box.className = 'checklist-item';
    box.innerHTML = `
      <input type="checkbox" class="checklist-checkbox">
      <div class="checklist-text-wrapper">
        <span class="checklist-text">${item.task}</span>
        <span class="checklist-time">${item.time}</span>
      </div>
    `;
    checklist.appendChild(box);
  });
}

// Export planner data as a clean file download
const exportBtn = document.getElementById('export-planner-btn');
exportBtn.addEventListener('click', () => {
  const items = document.querySelectorAll('.checklist-item');
  if (items.length === 0) {
    alert("Please generate your treatment summary first by entering symptoms or manual report details!");
    return;
  }
  
  let exportStr = `DIACARE AI PERSONAL LIFESTYLE PLAN\nGenerated on: ${new Date().toLocaleDateString()}\n==========================================\n\n`;
  items.forEach(el => {
    const text = el.querySelector('.checklist-text').innerText;
    const time = el.querySelector('.checklist-time').innerText;
    const checked = el.querySelector('.checklist-checkbox').checked ? "[x]" : "[ ]";
    exportStr += `${checked} ${time} - ${text}\n`;
  });
  
  exportStr += `\n==========================================\nMedical Warning: Maintain routine physician visits to calibrate prescriptions.`;
  
  const blob = new Blob([exportStr], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `diacare_daily_planner.txt`;
  a.click();
});

// 7. Progress Report Comparison Module
function setupCompareTracker() {
  const generateBtn = document.getElementById('generate-charts-btn');
  
  generateBtn.addEventListener('click', () => {
    const oldDate = document.getElementById('compare-old-date').value;
    const oldHba1c = parseFloat(document.getElementById('compare-old-hba1c').value);
    const oldGlucose = parseInt(document.getElementById('compare-old-glucose').value);
    
    const newDate = document.getElementById('compare-new-date').value;
    const newHba1c = parseFloat(document.getElementById('compare-new-hba1c').value);
    const newGlucose = parseInt(document.getElementById('compare-new-glucose').value);
    
    // Validate inputs
    if (!oldDate || isNaN(oldHba1c) || isNaN(oldGlucose) || !newDate || isNaN(newHba1c) || isNaN(newGlucose)) {
      alert("Please ensure all comparison fields are filled correctly!");
      return;
    }

    renderComparisonChart(oldDate, oldHba1c, oldGlucose, newDate, newHba1c, newGlucose);
  });
}

function renderComparisonChart(oldDate, oldHba1c, oldGlucose, newDate, newHba1c, newGlucose) {
  const ctx = document.getElementById('progress-chart-canvas').getContext('2d');
  
  if (progressChart) {
    progressChart.destroy();
  }

  // Draw chart using Chart.js CDN loaded in HTML
  progressChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: [oldDate, newDate],
      datasets: [
        {
          label: 'HbA1c Level (%)',
          data: [oldHba1c, newHba1c],
          backgroundColor: ['rgba(228, 228, 230, 0.75)', 'rgba(0, 0, 0, 0.85)'],
          borderColor: ['#e4e4e7', '#000000'],
          borderWidth: 1.5,
          yAxisID: 'y'
        },
        {
          label: 'Blood Glucose (mg/dL)',
          data: [oldGlucose, newGlucose],
          backgroundColor: ['rgba(161, 161, 170, 0.4)', 'rgba(0, 0, 0, 0.65)'],
          borderColor: ['#a1a1aa', '#000000'],
          borderWidth: 1.5,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          grid: { color: 'rgba(0, 0, 0, 0.08)' },
          ticks: { color: '#71717a' },
          title: { display: true, text: 'HbA1c Level (%)', color: '#71717a' }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          grid: { drawOnChartArea: false },
          ticks: { color: '#71717a' },
          title: { display: true, text: 'Glucose Level (mg/dL)', color: '#71717a' }
        },
        x: {
          ticks: { color: '#71717a' },
          grid: { color: 'rgba(0, 0, 0, 0.08)' }
        }
      },
      plugins: {
        legend: {
          labels: { color: '#09090b', font: { family: 'Plus Jakarta Sans' } }
        }
      }
    }
  });

  // Calculate percentage improvement
  const hba1cDiff = ((oldHba1c - newHba1c) / oldHba1c * 100).toFixed(1);
  const glucoseDiff = ((oldGlucose - newGlucose) / oldGlucose * 100).toFixed(1);
  
  let resultNote = "";
  if (hba1cDiff > 0) {
    resultNote = `Outstanding progress! Your HbA1c decreased by **${hba1cDiff}%** and blood glucose improved by **${glucoseDiff}%** between periods.`;
  } else {
    resultNote = "Readings show steady clinical bounds. Keep tracking and updating your daily planner checklists regularly.";
  }

  appendBotMessage(`<h3>Progress Comparison Generated</h3>
  I have generated the medical comparison chart for <strong>${oldDate}</strong> vs <strong>${newDate}</strong>.<br><br>
  - **HbA1c Trend:** ${oldHba1c}% ➔ ${newHba1c}%<br>
  - **Glucose Trend:** ${oldGlucose} mg/dL ➔ ${newGlucose} mg/dL<br><br>
  <strong>Clinical Trend Summary:</strong> ${resultNote}`);
}
