''' Define research-backed demonstration vacancies used by the optional sample-data management command. '''

def lines(*items):
    ''' Store ordered criteria in the same one-item-per-line format used by Job admin text areas. '''
    return '\n'.join(items)

SAMPLE_JOBS = [
    {
        'sample_key': 'backend-software-developer',
        'title': 'Software Developer — Backend Focus',
        'subtitle': 'Python, Django and PostgreSQL',
        'description': (
            '# Software Developer — Backend Focus\n\n'
            'We are looking for a software developer to join our engineering team working on web applications, internal systems and APIs.\n\n'
            'The role primarily involves backend development using Python and Django, with PostgreSQL used for data storage. Our applications expose REST '
            'APIs, integrate with external services and are deployed to Linux-based production environments.\n\n'
            'The developer will work on existing systems as well as build new functionality. Typical work includes designing backend features, working '
            'with databases, debugging production problems, reviewing existing code and collaborating with other developers.\n\n'
            'Candidates do not need experience with every technology in our stack. Strong experience with comparable technologies and evidence that the '
            'candidate can learn unfamiliar tools should also be considered.\n\n'
            '## Core requirements\n\n'
            '- Practical software development experience.\n'
            '- Competence in at least one modern programming language.\n'
            '- Experience building or maintaining backend applications.\n'
            '- Understanding of databases and working with stored data.\n'
            '- Ability to debug and solve technical problems.\n'
            '- Understanding of APIs or communication between software systems.\n'
            '- Ability to understand and modify existing code.\n'
            '- Ability to explain technical work they have personally contributed to.\n\n'
            '## Particularly relevant experience\n\n'
            'Python, Django or comparable backend frameworks, PostgreSQL or other relational databases, REST APIs, Linux, Git, testing, deployment, '
            'production systems, performance optimisation and cloud infrastructure are all relevant. None should individually determine the outcome.'
        ),
        'essential_requirements': lines(
            'Demonstrates practical software development experience through professional, freelance, academic, open-source or substantial personal work.',
            'Demonstrates practical programming competence in at least one modern language and can explain implementation decisions in work they personally contributed to.',
            'Demonstrates experience building or maintaining backend applications and understanding server-side request, business-logic or integration concerns.',
            'Demonstrates practical database understanding including stored data, schemas or models, queries and appropriate reasoning about data integrity or performance.',
            'Demonstrates a systematic ability to debug and solve technical problems using evidence rather than guesswork.',
            'Demonstrates understanding of APIs or other communication between software systems.',
            'Demonstrates the ability to understand and safely modify existing code rather than relying only on greenfield work.',
        ),
        'verification_requirements': '',
        'evaluation_questions': lines(
            'What evidence does the candidate provide that they have actually worked on software projects? Consider professional, '
            'freelance, academic, open-source and substantial personal projects.',
            'Does the conversation demonstrate practical programming knowledge? Consider languages, frameworks, implementation '
            'decisions and how software they worked on actually functioned.',
            'Does the candidate demonstrate experience relevant to backend application development? Consider servers, web '
            'applications, APIs, business logic, background processing, integrations and similar systems.',
            'What evidence is there that the candidate understands working with databases? Consider relational or non-relational '
            'databases, queries, schemas, indexes, migrations, performance, data modelling and practical database usage.',
            'Does the candidate describe situations where they diagnosed, investigated or solved technical problems? Consider '
            'debugging, performance issues, failures, unexpected behaviour and architectural problems.',
            'Does the candidate demonstrate an understanding of how different software systems communicate? Consider REST APIs, '
            'external services, authentication, webhooks, message queues or other integration techniques.',
            'Is there evidence that the candidate can understand and modify software they did not build entirely themselves? Consider '
            'maintenance work, team projects, debugging existing systems, extending features or working with unfamiliar code.',
            'When discussing projects or technologies, does the candidate provide enough technical detail to demonstrate meaningful '
            'understanding rather than only naming technologies? Consider explanations of how systems worked, decisions made, '
            'problems encountered and the candidate\'s own contribution.',
            'Where the candidate lacks direct experience with a technology in the job description, do they demonstrate closely '
            'related knowledge that would reasonably transfer? Do not require exact technology matches where the underlying '
            'engineering concepts are comparable.',
            'Are there important requirements of the role for which the interview provides little or no evidence? Consider whether '
            'these gaps are serious enough that a stage-two interview would probably not be worthwhile.',
            'Taking the technical evidence together, does the candidate appear capable of contributing productively as a software '
            'developer at approximately the level required by this role? Consider the overall body of evidence rather than treating '
            'individual answers as isolated tests.',
            'Would a human technical interview with this candidate be a worthwhile use of the engineering team\'s time? The threshold '
            'is not whether the candidate should receive the job; it is whether they have demonstrated enough relevant ability and '
            'potential to justify further human assessment.',
        ),
    },
    {
        'sample_key': 'frontend-web-developer',
        'title': 'Front-End Web Developer',
        'subtitle': 'React, TypeScript and accessible interfaces',
        'description': (
            'Develop accessible, responsive browser interfaces using semantic HTML, modern CSS, TypeScript and React. The role includes translating '
            'product requirements into maintainable components, managing client-side state and asynchronous API interactions, debugging browser '
            'behaviour, writing tests and improving performance without sacrificing usability. Accessibility is part of normal engineering work: '
            'interactive controls should use appropriate semantics, keyboard operation and understandable focus behaviour, and interfaces should '
            'remain usable across screen sizes and assistive technologies. Experience with another modern component framework is transferable when '
            'the underlying browser and UI engineering knowledge is strong.'
        ),
        'essential_requirements': lines(
            'Demonstrates practical JavaScript or TypeScript experience and a sound understanding of browser-based application behaviour.',
            'Demonstrates practical component-based UI development experience with React or a closely comparable modern framework.',
            'Demonstrates competent HTML and CSS layout knowledge, including responsive design and the ability to diagnose real rendering problems.',
            'Demonstrates practical accessibility awareness including semantic controls, keyboard interaction and usable focus behaviour.',
        ),
        'verification_requirements': '',
        'evaluation_questions': lines(
            'What evidence shows that the candidate understands component state, rendering and side effects rather than only framework syntax?',
            'What evidence shows that the candidate can build and debug responsive layouts using modern CSS layout systems?',
            'How well does the candidate understand semantic HTML and why native controls often provide better accessibility than generic elements?',
            'What evidence shows practical handling of asynchronous API requests, loading states, failures and stale or cancelled work?',
            'What evidence shows that the candidate can identify and improve front-end performance without premature optimisation?',
            'What evidence shows effective testing and debugging across browsers and realistic user interactions?',
            'How well can the candidate transfer knowledge between React and other frameworks while reasoning from browser fundamentals?',
        ),
    },
    {
        'sample_key': 'embedded-firmware-engineer',
        'title': 'Embedded Firmware Engineer',
        'subtitle': 'C, microcontrollers and real-time systems',
        'description': (
            'Develop and debug firmware for microcontroller-based products using C and embedded development tools. Work includes peripheral drivers, '
            'interrupt-driven I/O, timing-sensitive behaviour, memory- and power-constrained design, hardware bring-up and communication interfaces '
            'such as UART, SPI and I2C. Some products use an RTOS, where tasks, queues, semaphores or mutexes must be chosen with an understanding of '
            'concurrency and interrupt context. Engineers use datasheets, schematics, debuggers, logic analysers or oscilloscopes to isolate faults '
            'that may cross the hardware/software boundary. We value reasoning about low-level behaviour more than memorising register addresses or '
            'vendor-specific APIs.'
        ),
        'essential_requirements': lines(
            'Demonstrates practical C programming experience involving memory, pointers, data representation and resource-constrained software.',
            'Demonstrates practical experience with microcontrollers or comparable embedded targets, including peripherals and hardware/software interaction.',
            'Demonstrates sound reasoning about interrupts, concurrency, timing and safe communication between asynchronous execution contexts.',
            'Demonstrates a systematic embedded-debugging approach using appropriate hardware and software evidence.',
        ),
        'verification_requirements': '',
        'evaluation_questions': lines(
            'What evidence shows that the candidate understands volatile state, memory lifetime, stack/heap constraints and common embedded C failure modes?',
            'What evidence shows practical use of UART, SPI, I2C, GPIO, timers, ADCs or comparable microcontroller peripherals?',
            'How well does the candidate reason about work that belongs in an interrupt service routine versus deferred task or main-loop processing?',
            'What evidence shows understanding of RTOS primitives such as tasks, queues, semaphores and mutexes, including priority or blocking concerns?',
            'What evidence shows that the candidate can diagnose faults using datasheets, registers, debugger state, traces, logic analysers or oscilloscopes?',
            'How well does the candidate reason about race conditions, timing bugs and failures that appear only under particular hardware conditions?',
            'What evidence shows disciplined testing, code review and documentation appropriate to firmware that interacts directly with hardware?',
        ),
    },
    {
        'sample_key': 'registered-nurse-acute-adult',
        'title': 'Registered Nurse',
        'subtitle': 'Adult acute medical ward',
        'description': (
            'Provide safe, compassionate and evidence-based nursing care for adults on a busy acute medical ward in the UK. The role requires ongoing '
            'assessment, care planning, clinical observations, medicines safety, infection prevention, accurate documentation and effective handover '
            'within a multidisciplinary team. Nurses must recognise and respond to deterioration, including interpreting changes in observations and '
            'using local escalation processes such as NEWS2 alongside structured assessment approaches such as ABCDE. The nurse must work within their '
            'scope of competence, seek appropriate help early, communicate clearly with patients and colleagues, preserve dignity and escalate safety '
            'concerns. Current professional registration is verified separately from the interview.'
        ),
        'essential_requirements': lines(
            'Demonstrates clinical reasoning and prioritisation consistent with safe adult nursing practice in an acute-care environment.',
            'Demonstrates competent recognition and escalation of patient deterioration using observations, structured assessment and appropriate clinical communication.',
            'Demonstrates sound medication-safety reasoning, including checking prescriptions, allergies, patient factors, documentation and working within scope.',
            'Demonstrates practical understanding of infection prevention, patient dignity, documentation and multidisciplinary communication in routine nursing care.',
        ),
        'verification_requirements': lines(
            'Current Nursing and Midwifery Council registration permitting practice as a registered nurse in the UK.',
        ),
        'evaluation_questions': lines(
            'What evidence shows that the candidate can assess a deteriorating adult using an ABCDE-style approach and escalate concerns appropriately?',
            'What evidence shows meaningful understanding of clinical observations, trends and NEWS2 rather than merely recognising the terminology?',
            'How well does the candidate prioritise competing patient needs and recognise when they need senior or multidisciplinary support?',
            'What evidence shows safe medicines practice and an ability to respond appropriately to uncertainty, omitted doses, allergies or unexpected findings?',
            'What evidence shows effective structured handover and communication, for example using SBAR or an equivalent approach?',
            'What evidence shows that the candidate understands accountability, scope of competence and the need to raise concerns when safety may be compromised?',
            'What evidence shows person-centred care, consent, dignity, safeguarding awareness and accurate contemporaneous documentation?',
        ),
    },
    {
        'sample_key': 'commercial-cleaner',
        'title': 'Commercial Cleaner',
        'subtitle': 'Offices and shared facilities',
        'description': (
            'Clean offices, washrooms, kitchens and shared facilities to an agreed schedule. Duties include vacuuming, mopping, surface cleaning, waste '
            'handling, replenishing consumables and reporting damage, hazards or low stock. Cleaning products must be used, stored and diluted according '
            'to instructions and workplace COSHH controls, with suitable PPE where required. The role requires dependable attendance, attention to detail, '
            'safe working, sensible prevention of cross-contamination and the ability to organise tasks independently. Previous commercial cleaning '
            'experience is useful but is not required for this entry-level vacancy when the candidate can demonstrate reliability and safe working habits.'
        ),
        'essential_requirements': lines(
            'Demonstrates reliability, punctuality and the ability to complete an assigned cleaning schedule with limited supervision.',
            'Demonstrates safe reasoning about cleaning chemicals, product instructions, COSHH controls, storage and appropriate PPE.',
            'Demonstrates practical understanding of cleaning methods, hygiene and avoiding cross-contamination between areas.',
            'Demonstrates attention to detail and appropriate action when encountering hazards, damage, spills or tasks outside normal instructions.',
        ),
        'verification_requirements': '',
        'evaluation_questions': lines(
            'What evidence shows that the candidate can organise and prioritise a realistic cleaning workload?',
            'What evidence shows sensible handling of unfamiliar products or chemicals rather than guessing how they should be used?',
            'What evidence shows understanding of separating equipment or methods where cross-contamination could matter?',
            'How would the candidate respond to a spill, damaged equipment or another hazard that they cannot safely resolve alone?',
            'What evidence shows that the candidate can maintain consistent standards when working independently or under time pressure?',
            'What evidence shows appropriate communication with supervisors, colleagues or building users about problems and completed work?',
        ),
    },
    {
        'sample_key': 'installation-electrician',
        'title': 'Installation Electrician',
        'subtitle': 'Commercial electrical installation and maintenance',
        'description': (
            'Install, inspect, test, maintain and fault-find electrical systems in commercial buildings. Work includes interpreting drawings and circuit '
            'information, installing cabling and accessories, using appropriate test instruments, identifying defects and documenting results. Safe '
            'isolation and proving circuits dead before work are fundamental. The electrician must understand protective devices, earthing and bonding, '
            'basic fault-finding principles and when work must stop or be escalated. The role requires recognised practical training and experience; '
            'qualifications and certification are checked separately rather than accepted solely from interview statements.'
        ),
        'essential_requirements': lines(
            'Demonstrates practical electrical installation or maintenance experience and can explain work they personally completed.',
            'Demonstrates safe-isolation reasoning, appropriate use of test equipment and a consistent approach to preventing electrical injury.',
            'Demonstrates practical fault-finding ability using circuit information, measurements and systematic elimination of plausible causes.',
            'Demonstrates understanding of protective devices, earthing, bonding and the need to verify completed work by inspection and testing.',
        ),
        'verification_requirements': lines(
            'Relevant Level 3 electrical qualification or recognised experienced-worker equivalent appropriate to the installation role.',
        ),
        'evaluation_questions': lines(
            'What evidence shows that the candidate can describe a safe isolation process and explain why each stage matters?',
            'What evidence shows competent use and interpretation of electrical test instruments rather than unsafe trial-and-error fault finding?',
            'How well can the candidate reason from symptoms, drawings and measurements to locate an electrical fault?',
            'What evidence shows understanding of protective devices, earthing and bonding at a practical working level?',
            'What evidence shows that the candidate knows when a task is outside their competence or requires escalation?',
            'What evidence shows careful inspection, testing, documentation and communication after installation or repair work?',
        ),
    },
    {
        'sample_key': 'customer-service-advisor',
        'title': 'Customer Service Advisor',
        'subtitle': 'Phone, email and webchat support',
        'description': (
            'Respond to customer questions through phone, email and webchat, explain products and policies clearly, investigate routine account or order '
            'problems, record accurate case notes and arrange escalation when an issue cannot be resolved at first contact. The role includes handling '
            'complaints and emotionally charged conversations while remaining calm and professional. Advisors use a customer-management system, follow '
            'identity and data-handling procedures, distinguish facts from assumptions and avoid making promises they cannot fulfil. Previous contact-centre '
            'experience is useful but strong transferable customer-facing experience is acceptable.'
        ),
        'essential_requirements': lines(
            'Demonstrates active listening and clear communication with customers who may be confused, frustrated or upset.',
            'Demonstrates a structured problem-solving approach that gathers relevant facts before proposing a resolution.',
            'Demonstrates accurate record keeping and appropriate handling of customer information in computer-based systems.',
            'Demonstrates judgement about ownership, escalation and avoiding promises or actions outside their authority.',
        ),
        'verification_requirements': '',
        'evaluation_questions': lines(
            'What evidence shows that the candidate can de-escalate a difficult conversation without becoming defensive or dismissive?',
            'What evidence shows that the candidate can explain a policy or limitation clearly while still trying to help the customer?',
            'How well does the candidate distinguish a symptom from the underlying customer problem and gather the information needed to investigate?',
            'What evidence shows concise and accurate case-note or CRM habits that another colleague could rely on?',
            'What evidence shows good judgement about when to resolve an issue personally and when to escalate it?',
            'What evidence shows resilience, teamwork and the ability to maintain service quality during busy periods?',
        ),
    },
    {
        'sample_key': 'management-accountant',
        'title': 'Management Accountant',
        'subtitle': 'Budgeting, forecasting and performance analysis',
        'description': (
            'Prepare and interpret management information that helps business leaders understand financial performance and make decisions. The role '
            'includes month-end processes, management accounts, budgeting, forecasting, variance analysis, cost and margin analysis, reconciliations '
            'and maintaining appropriate financial controls. The accountant should be able to explain why actual results differ from plan, distinguish '
            'timing effects from underlying performance and communicate financial findings to non-finance colleagues. Spreadsheet and finance-system '
            'skills are expected, but the interview focuses on accounting reasoning rather than memorising a particular software package.'
        ),
        'essential_requirements': lines(
            'Demonstrates practical management-accounting experience including month-end reporting, reconciliations and preparation or review of management accounts.',
            'Demonstrates competent budgeting, forecasting and variance-analysis reasoning and can distinguish operational drivers from accounting presentation.',
            'Demonstrates practical understanding of accruals, prepayments, cost allocation, margins and the controls needed for reliable internal reporting.',
            'Demonstrates the ability to turn financial and non-financial data into clear analysis for business decision-makers.',
        ),
        'verification_requirements': lines(
            'CIMA, ACCA, ACA or comparable professional accountancy qualification, or documented active progression toward one where the vacancy '
            'permits part-qualified applicants.',
        ),
        'evaluation_questions': lines(
            'What evidence shows that the candidate can explain a month-end close process and identify where inaccurate cut-off or classification could distort results?',
            'How well can the candidate investigate a material budget variance and separate volume, price, mix, timing or one-off effects where relevant?',
            'What evidence shows understanding of accruals, prepayments, balance-sheet reconciliations and why they matter?',
            'What evidence shows practical forecasting judgement rather than simply extending historical numbers?',
            'How well can the candidate explain margins, cost behaviour and performance drivers to a non-finance stakeholder?',
            'What evidence shows appropriate financial controls, review discipline and willingness to challenge implausible data?',
            'What evidence shows useful spreadsheet or finance-system skills without overvaluing memorised software-specific shortcuts?',
        ),
    },
    {
        'sample_key': 'secondary-science-teacher',
        'title': 'Secondary School Science Teacher',
        'subtitle': 'Key Stage 3 and GCSE science',
        'description': (
            'Plan and teach engaging science lessons for pupils at Key Stage 3 and GCSE in an English maintained secondary school. The teacher must '
            'have secure subject and curriculum knowledge, explain scientific ideas accurately, identify misconceptions, assess pupil understanding '
            'and adapt teaching so pupils with different starting points can make progress. The role includes practical science, classroom management, '
            'marking and feedback, safeguarding, collaboration with colleagues and communication with parents or carers. Qualified Teacher Status is '
            'verified separately. The interview tests teaching judgement and science understanding rather than recall of one school\'s internal procedures.'
        ),
        'essential_requirements': lines(
            'Demonstrates secure science subject knowledge sufficient to teach Key Stage 3 and GCSE content accurately and respond to common misconceptions.',
            'Demonstrates practical lesson planning and explanation skills that connect learning objectives, prior knowledge, activities and checks for understanding.',
            'Demonstrates effective classroom-management judgement that maintains a safe, respectful environment while supporting learning.',
            'Demonstrates appropriate safeguarding awareness, professional boundaries and willingness to follow school escalation procedures.',
        ),
        'verification_requirements': lines(
            'Qualified Teacher Status for teaching in an English maintained secondary school, or a recognised status that the employer can lawfully accept for the appointment.',
        ),
        'evaluation_questions': lines(
            'What evidence shows that the candidate can explain a scientific concept accurately and adapt the explanation when a pupil does not understand?',
            'What evidence shows that the candidate can identify misconceptions and use assessment to decide what to teach next?',
            'How well does the candidate plan practical science with appropriate risk awareness, instructions and learning purpose?',
            'What evidence shows that the candidate can set high expectations while adapting teaching for different prior attainment or additional needs?',
            'What evidence shows calm, proportionate classroom-management decisions rather than relying only on sanctions?',
            'What evidence shows appropriate safeguarding judgement, record keeping and escalation when a pupil discloses a concern?',
            'What evidence shows collaboration with colleagues and clear communication with pupils, parents or carers about progress?',
        ),
    },
    {
        'sample_key': 'warehouse-operative',
        'title': 'Warehouse Operative',
        'subtitle': 'Goods-in, picking and dispatch',
        'description': (
            'Receive deliveries, check goods and paperwork, put stock away safely, pick customer orders accurately, pack items for dispatch and keep '
            'warehouse locations orderly. The role uses handheld scanners or a warehouse-management system to confirm stock movements and requires '
            'care when dealing with damaged, missing or incorrectly labelled items. Operatives must follow site safety rules, use manual-handling or '
            'lifting equipment appropriately, protect pedestrians and colleagues around moving equipment and report hazards promptly. Previous warehouse '
            'experience is useful but not mandatory when the candidate demonstrates accuracy, reliability and safe working behaviour.'
        ),
        'essential_requirements': lines(
            'Demonstrates reliable and accurate working habits when receiving, locating, picking, checking or dispatching goods.',
            'Demonstrates safe manual-handling reasoning and appropriate respect for lifting equipment, vehicle routes and warehouse hazards.',
            'Demonstrates practical judgement when stock, labels, quantities, packaging or paperwork do not match expectations.',
            'Demonstrates the ability to follow process, use basic digital scanning or stock systems and communicate problems during busy work.',
        ),
        'verification_requirements': '',
        'evaluation_questions': lines(
            'What evidence shows that the candidate can balance picking speed with accuracy and avoid propagating stock errors?',
            'How would the candidate respond to damaged goods, a quantity mismatch or an item stored in the wrong location?',
            'What evidence shows safe judgement about manual handling and when to use equipment or ask for assistance?',
            'What evidence shows awareness of pedestrian, vehicle and general housekeeping risks in a busy warehouse?',
            'What evidence shows that the candidate can use scanners or warehouse systems carefully and recover from a data-entry or scanning mistake?',
            'What evidence shows teamwork, communication and reliability during high-volume or time-sensitive periods?',
        ),
    },
]
