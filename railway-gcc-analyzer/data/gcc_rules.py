"""
data/gcc_rules.py

Railway General Conditions of Contract (GCC) Rules Dataset.
Contains 25 realistic GCC clauses covering all major contract risk categories.
"""

GCC_RULES = [
    {
        "clause_id": "GCC-47.1",
        "clause_title": "Termination by Employer",
        "clause_text": (
            "The Employer shall be entitled to terminate this Contract at any time by issuing a "
            "Termination Notice to the Contractor, provided that such notice shall not be issued "
            "before the expiry of a cure period of 28 (twenty-eight) days from the date of a prior "
            "written notice to the Contractor specifying the default. The Employer may terminate if "
            "the Contractor: (a) abandons the Works or repudiates the Contract; (b) without reasonable "
            "excuse fails to proceed with the Works in accordance with the approved programme; (c) "
            "subcontracts the whole or any part of the Works without prior written consent; (d) becomes "
            "insolvent, has a receiving order made against it, compounds with creditors, or carries on "
            "business under a receiver or manager. Upon termination, the Employer shall be entitled to "
            "forfeit the Performance Bank Guarantee and recover all losses, costs, and damages suffered "
            "as a consequence of the Contractor's default, including any additional costs of completing "
            "the Works by an alternative contractor."
        ),
        "risk_category": "HIGH",
        "keywords": [
            "termination", "employer", "cure period", "default", "performance bank guarantee",
            "abandonment", "repudiation", "insolvency", "forfeiture"
        ]
    },
    {
        "clause_id": "GCC-48.1",
        "clause_title": "Termination by Contractor",
        "clause_text": (
            "The Contractor shall be entitled to terminate this Contract by issuing a Termination Notice "
            "to the Employer if: (a) the Employer fails to pay any amount due under the Contract within "
            "56 (fifty-six) days after the expiry of the time for payment and has not remedied the default "
            "within 28 (twenty-eight) days of receiving a written notice from the Contractor; (b) the "
            "Employer substantially fails to perform its obligations under the Contract; (c) a prolonged "
            "suspension of the Works ordered by the Employer exceeds 84 (eighty-four) days and is not "
            "attributable to any default by the Contractor; (d) the Employer becomes insolvent or unable "
            "to pay its debts. Upon termination by the Contractor, the Employer shall pay the Contractor "
            "the value of all work executed, costs of plant and materials ordered and delivered, loss of "
            "anticipated profit calculated at the agreed margin, and the cost of demobilization."
        ),
        "risk_category": "HIGH",
        "keywords": [
            "termination", "contractor", "non-payment", "suspension", "demobilization",
            "loss of profit", "employer default", "prolonged suspension"
        ]
    },
    {
        "clause_id": "GCC-49.1",
        "clause_title": "Liquidated Damages for Delay",
        "clause_text": (
            "If the Contractor fails to complete the Works or any Section by the respective Time for "
            "Completion, the Contractor shall pay to the Employer Liquidated Damages (LD) at the rate "
            "specified in the Contract Data for each day or part of a day that shall elapse between the "
            "Time for Completion and the actual date of completion of the Works or the relevant Section. "
            "The total amount of Liquidated Damages shall not exceed the maximum limit stated in the "
            "Contract Data, which shall not be less than 10% (ten percent) of the Contract Price. "
            "Liquidated Damages shall be the Employer's sole remedy for the Contractor's failure to "
            "achieve the Time for Completion and shall be deducted from any amounts due to the Contractor "
            "under the Contract or recovered from the Performance Security. The Employer shall not be "
            "required to prove actual damage suffered. Where Sectional Completion applies, LD shall be "
            "assessed separately for each Section in accordance with the respective completion dates."
        ),
        "risk_category": "HIGH",
        "keywords": [
            "liquidated damages", "delay", "time for completion", "penalty", "sectional completion",
            "performance security", "contract price", "deduction", "LD cap"
        ]
    },
    {
        "clause_id": "GCC-50.1",
        "clause_title": "Extension of Time for Completion",
        "clause_text": (
            "The Contractor shall be entitled to an extension of the Time for Completion if and to the "
            "extent that the completion of the Works is or will be delayed by any of the following causes: "
            "(a) a Variation issued by the Employer which materially affects the Works; (b) exceptionally "
            "adverse climatic conditions at the Site that could not have been foreseen; (c) physical "
            "obstructions or conditions not foreseeable by an experienced contractor; (d) any delay caused "
            "by the Employer or Employer's Personnel; (e) Force Majeure events as defined herein. The "
            "Contractor must give notice of a claim for extension of time within 28 (twenty-eight) days "
            "of the commencement of the delaying event. The claim must include a programme showing the "
            "delay, its cause, and the duration of extension required. Failure to give timely notice shall "
            "not bar the claim but may reduce the Employer's obligation to grant an extension for the "
            "period prior to the notice. The Engineer shall assess the claim and grant a fair extension."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "extension of time", "EOT", "delay", "variation", "force majeure", "notice", "claim",
            "engineer", "programme", "adverse conditions"
        ]
    },
    {
        "clause_id": "GCC-14.1",
        "clause_title": "Payment Terms and Milestone Certificates",
        "clause_text": (
            "The Employer shall make interim payments to the Contractor in accordance with the Payment "
            "Schedule set out in the Contract Data. The Contractor shall submit an Interim Payment "
            "Application to the Engineer at the end of each calendar month, supported by measurement "
            "records, materials on site schedules, and such other documentation as the Engineer may "
            "require. The Engineer shall issue an Interim Payment Certificate within 28 (twenty-eight) "
            "days of receiving a fully documented application. The Employer shall make payment within "
            "28 (twenty-eight) days of the date of issue of the Payment Certificate. Retention of "
            "5% (five percent) shall be deducted from each interim payment. One half of the Retention "
            "Money shall be released upon issue of the Taking Over Certificate; the remaining half shall "
            "be released upon the expiry of the Defects Notification Period and issue of the Performance "
            "Certificate. If the Engineer fails to issue a Payment Certificate in time, the Contractor "
            "shall be entitled to financing charges at the rate specified in the Contract Data."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "payment", "interim payment", "payment certificate", "retention", "milestone",
            "engineer", "taking over certificate", "financing charges", "deduction", "measurement"
        ]
    },
    {
        "clause_id": "GCC-19.1",
        "clause_title": "Force Majeure",
        "clause_text": (
            "Force Majeure means an exceptional event or circumstance which is beyond a Party's control, "
            "which such Party could not reasonably have provided against before entering into the Contract, "
            "which having arisen such Party could not reasonably have avoided or overcome, and which is not "
            "substantially attributable to the other Party. Force Majeure includes but is not limited to: "
            "(a) war, hostilities, invasion, act of foreign enemies; (b) rebellion, terrorism, sabotage "
            "by third parties; (c) riot, commotion, disorder, strike or lockout by persons other than "
            "the Contractor's Personnel; (d) munitions of war, explosive materials, ionising radiation; "
            "(e) natural catastrophes such as earthquakes, hurricanes, typhoons, or volcanic activity. "
            "A Party claiming Force Majeure shall give notice to the other Party within 14 (fourteen) days "
            "of becoming aware of the event. Neither Party shall be entitled to terminate the Contract "
            "unless the Force Majeure event continues for a period exceeding 84 (eighty-four) days. "
            "The Contractor shall be entitled to an extension of time but not to additional payment for "
            "delay arising from Force Majeure unless expressly agreed otherwise."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "force majeure", "exceptional event", "war", "natural disaster", "notice",
            "extension of time", "termination", "beyond control", "unforeseeable"
        ]
    },
    {
        "clause_id": "GCC-20.1",
        "clause_title": "Dispute Resolution and Arbitration",
        "clause_text": (
            "Any dispute or difference arising out of or in connection with this Contract, including any "
            "question regarding its existence, validity, or termination, shall be referred in the first "
            "instance to the Engineer for determination. The Engineer shall issue a determination within "
            "28 (twenty-eight) days of referral. If either Party is dissatisfied with the Engineer's "
            "determination, or if the Engineer fails to give a determination within the specified time, "
            "either Party may, within 28 (twenty-eight) days, give notice of dissatisfaction. Disputes "
            "shall then be referred to arbitration under the Arbitration and Conciliation Act, 1996 "
            "(or as amended). The arbitral tribunal shall consist of a sole arbitrator mutually agreed "
            "upon by the Parties, failing which appointed by the relevant Railway Authority. The seat of "
            "arbitration shall be New Delhi, India. The language of arbitration shall be English. "
            "Pending the resolution of any dispute, the Contractor shall continue to carry out the Works "
            "in accordance with the Contract. The Engineer's decision shall be binding unless revised "
            "by the arbitral tribunal."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "dispute", "arbitration", "engineer determination", "Arbitration Act", "conciliation",
            "arbitral tribunal", "seat of arbitration", "New Delhi", "notice of dissatisfaction"
        ]
    },
    {
        "clause_id": "GCC-13.1",
        "clause_title": "Variations and Scope Changes",
        "clause_text": (
            "The Engineer may initiate Variations at any time prior to the issue of the Taking Over "
            "Certificate by issuing a Variation Order. Each Variation may include: (a) changes to the "
            "quantities of any item of work included in the Contract; (b) changes to the quality and "
            "other characteristics of any item of work; (c) changes to the levels, positions, and/or "
            "dimensions of any part of the Works; (d) omission of any work unless it is to be carried "
            "out by others; (e) any additional work necessary for the completion of the Works. The "
            "total value of Variations shall not exceed 25% (twenty-five percent) of the original "
            "Contract Price without the prior approval of the Competent Authority. The Contractor shall "
            "not make any changes to the Works without a Variation Order. Valuation of Variations shall "
            "be at rates agreed between the Engineer and the Contractor, or failing agreement, at rates "
            "derived from the Bill of Quantities, or at reasonable market rates. Claims for additional "
            "time or cost arising from Variations must be submitted within 28 days of the Variation Order."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "variation", "scope change", "variation order", "engineer", "bill of quantities",
            "contract price", "omission", "25 percent limit", "valuation", "claim"
        ]
    },
    {
        "clause_id": "GCC-18.1",
        "clause_title": "Insurance and Indemnity",
        "clause_text": (
            "The Contractor shall, prior to commencement of the Works, effect and maintain the following "
            "insurances: (a) Works All Risk Insurance covering the full reinstatement value of the Works "
            "including materials on site, for the duration of the Contract; (b) Third Party Liability "
            "Insurance with a minimum limit of INR 5 Crore per occurrence; (c) Contractor's Plant and "
            "Equipment Insurance; (d) Workmen's Compensation Insurance as required under the Employees' "
            "Compensation Act, 1923 and applicable state legislation. All policies shall name the Employer "
            "as an additional insured. The Contractor shall indemnify and hold harmless the Employer from "
            "and against all claims, damages, losses, and expenses arising out of the Works, unless caused "
            "by the Employer's negligence or breach of Contract. The Contractor shall provide certified "
            "copies of all insurance policies to the Engineer before commencement of Works and shall "
            "maintain such insurance in force until the issue of the Defects Notification Period Certificate."
        ),
        "risk_category": "HIGH",
        "keywords": [
            "insurance", "indemnity", "works all risk", "third party liability", "workmen compensation",
            "additional insured", "Employees Compensation Act", "hold harmless", "reinstatement value"
        ]
    },
    {
        "clause_id": "GCC-11.1",
        "clause_title": "Defects Liability Period",
        "clause_text": (
            "The Defects Notification Period (DNP) shall be as stated in the Contract Data, typically "
            "12 (twelve) months from the date of the Taking Over Certificate for the whole of the Works, "
            "or such other period as may be specified for any Section or part of the Works. During the "
            "DNP, the Contractor shall be obligated to rectify all defects, shrinkages, or other faults "
            "which appear in the Works and which are due to materials or workmanship not being in "
            "accordance with the Contract. The Contractor shall complete such remedial work at no cost "
            "to the Employer. If the Contractor fails to remedy a defect within a reasonable time, "
            "the Employer shall be entitled to carry out the remedial work itself or through other "
            "contractors and to recover the cost from the Contractor or from the Performance Security. "
            "The DNP shall be extended by a period equal to the period during which the Works cannot "
            "be used due to any defect. The Performance Certificate shall be issued at the expiry of "
            "the last DNP, after all outstanding defects have been rectified."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "defects liability", "defects notification period", "DNP", "taking over certificate",
            "remedial work", "performance certificate", "workmanship", "materials", "rectification"
        ]
    },
    {
        "clause_id": "GCC-13.8",
        "clause_title": "Price Escalation — IEEMA and WPI Clauses",
        "clause_text": (
            "The Contract Price shall be subject to adjustment for fluctuations in the cost of labour, "
            "materials, and fuel in accordance with the formulae set out in the Contract Data. The price "
            "adjustment for materials shall be based on the Wholesale Price Index (WPI) published by the "
            "Office of the Economic Adviser, Ministry of Commerce and Industry, Government of India. "
            "For electrical and electromechanical components, the price adjustment shall be based on "
            "the IEEMA (Indian Electrical and Electronics Manufacturers' Association) Price Variation "
            "Formula as applicable. The base indices shall be those prevailing during the month of "
            "submission of the Contractor's Tender. No price adjustment shall be payable for work "
            "executed after the contractual Time for Completion or any extended period attributable "
            "to the Contractor's default. The adjustment shall be calculated monthly and included "
            "in Interim Payment Certificates. If the WPI or IEEMA index is discontinued, the Parties "
            "shall agree on a suitable replacement index within 30 days."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "price escalation", "WPI", "IEEMA", "price variation", "wholesale price index",
            "labour escalation", "material escalation", "base index", "adjustment formula"
        ]
    },
    {
        "clause_id": "GCC-4.2",
        "clause_title": "Performance Bank Guarantee",
        "clause_text": (
            "The Contractor shall, within 21 (twenty-one) days after receiving the Letter of Acceptance, "
            "furnish the Employer with a Performance Security in the amount of 10% (ten percent) of the "
            "Contract Price. The Performance Security shall be in the form of an unconditional Bank "
            "Guarantee from a scheduled commercial bank acceptable to the Employer, substantially in "
            "the format annexed to the Contract. The Performance Security shall be valid until the "
            "expiry of the Defects Notification Period plus 60 (sixty) days. The Performance Security "
            "shall be forfeited if the Contractor is in material breach of its obligations under the "
            "Contract. The Employer shall return the Performance Security to the Contractor within "
            "28 (twenty-eight) days of the issue of the Performance Certificate. The Contractor shall "
            "extend the validity of the Performance Security if the Time for Completion is extended. "
            "Failure to furnish the Performance Security within the stipulated time shall entitle the "
            "Employer to terminate the Contract."
        ),
        "risk_category": "HIGH",
        "keywords": [
            "performance bank guarantee", "performance security", "bank guarantee", "unconditional",
            "letter of acceptance", "forfeiture", "scheduled bank", "10 percent", "termination"
        ]
    },
    {
        "clause_id": "GCC-14.7",
        "clause_title": "Mobilization Advance and Recovery",
        "clause_text": (
            "The Employer shall pay to the Contractor a Mobilization Advance of 10% (ten percent) of the "
            "Contract Price, subject to the Contractor furnishing an unconditional Bank Guarantee from "
            "an acceptable scheduled bank for the full amount of the advance. The Mobilization Advance "
            "shall be paid in a single installment within 28 (twenty-eight) days of commencement of "
            "the Works and upon submission of the bank guarantee. Recovery of the Mobilization Advance "
            "shall commence when the cumulative value of work certified in the Interim Payment "
            "Certificates reaches 10% (ten percent) of the Contract Price, and shall be recovered in "
            "equal proportions from subsequent Interim Payments until the full advance is recovered "
            "by the time the cumulative work certified reaches 80% (eighty percent) of the Contract "
            "Price. Interest on the Mobilization Advance shall be charged at 10% (ten percent) per "
            "annum from the date of payment. The bank guarantee for the advance shall be reduced "
            "proportionately as recovery is made."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "mobilization advance", "advance payment", "recovery", "bank guarantee", "interest",
            "cumulative work", "proportionate recovery", "interim payment", "10 percent"
        ]
    },
    {
        "clause_id": "GCC-4.4",
        "clause_title": "Sub-contracting Restrictions",
        "clause_text": (
            "The Contractor shall not sub-contract the whole of the Works. The Contractor shall not "
            "sub-contract any part of the Works without the prior written consent of the Engineer, "
            "which shall not be unreasonably withheld. Any consent to sub-contracting shall not relieve "
            "the Contractor of any of its obligations or liabilities under the Contract. The Contractor "
            "shall be responsible for the acts and omissions of all sub-contractors and their employees "
            "as if they were the acts or omissions of the Contractor. Sub-contractors must possess "
            "the necessary technical qualification and financial standing required for the particular "
            "sub-contracted work, as determined by the Engineer. The Contractor shall not sub-contract "
            "to firms that have been debarred or blacklisted by any Ministry of the Government of India "
            "or by the Ministry of Railways. The list of proposed sub-contractors shall be submitted "
            "to the Engineer for approval at least 28 (twenty-eight) days before the intended "
            "commencement of their work."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "sub-contracting", "subcontractor", "engineer consent", "debarred", "blacklisted",
            "liability", "acts and omissions", "written consent", "Ministry of Railways"
        ]
    },
    {
        "clause_id": "GCC-1.4",
        "clause_title": "Governing Law and Jurisdiction",
        "clause_text": (
            "This Contract shall be governed by and construed in accordance with the laws of India. "
            "The Parties submit to the exclusive jurisdiction of the courts located at the place "
            "specified in the Contract Data for all disputes arising out of or in connection with "
            "this Contract that are not referred to arbitration under Clause 20. All notices, "
            "communications, and documents under this Contract shall be in the English language, "
            "or if in any other language, shall be accompanied by a certified English translation "
            "which shall govern in the event of any ambiguity. The Contract shall be construed in "
            "accordance with the Indian Contract Act, 1872, the Specific Relief Act, 1963, and all "
            "applicable regulations issued by the Ministry of Railways, Government of India, including "
            "the Indian Railways General Conditions of Contract (GCC) as amended from time to time. "
            "In the event of any conflict between the GCC and any Special Conditions of Contract, "
            "the Special Conditions shall prevail."
        ),
        "risk_category": "LOW",
        "keywords": [
            "governing law", "jurisdiction", "India", "courts", "Indian Contract Act",
            "Ministry of Railways", "English language", "Special Conditions", "arbitration"
        ]
    },
    {
        "clause_id": "GCC-8.1",
        "clause_title": "Commencement and Programme of Works",
        "clause_text": (
            "The Contractor shall commence the Works on the date of the Letter to Proceed or within "
            "such period as stated in the Contract Data. The Contractor shall submit to the Engineer "
            "a detailed programme of the Works within 28 (twenty-eight) days of the Commencement Date. "
            "The programme shall include: (a) the order in which the Contractor intends to carry out "
            "the Works, including anticipated timing of each stage; (b) periods for reviews required "
            "by the Employer; (c) a general description of the methods the Contractor intends to adopt "
            "for executing the principal sections of the Works; (d) details of the resources the "
            "Contractor will use. The Engineer shall respond within 21 days with comments or approval. "
            "If the actual progress falls behind the approved programme, the Contractor shall submit "
            "a revised programme showing the steps to be taken to achieve completion by the Time for "
            "Completion, without additional cost to the Employer. The Contractor's obligation to "
            "complete by the Time for Completion is not relieved by any approval of the programme."
        ),
        "risk_category": "LOW",
        "keywords": [
            "commencement", "programme", "Letter to Proceed", "resources", "methods",
            "engineer approval", "revised programme", "time for completion", "schedule"
        ]
    },
    {
        "clause_id": "GCC-4.1",
        "clause_title": "Contractor's General Obligations",
        "clause_text": (
            "The Contractor shall design (to the extent specified in the Contract), execute, and complete "
            "the Works in accordance with the Contract and with the Engineer's instructions, and shall "
            "remedy any defects in the Works. The Contractor shall provide the Plant, Documents, and "
            "other Goods as specified in the Contract, and all labour, management, and other services "
            "required for the proper execution of the Works. The Contractor shall carry out the Works "
            "in a proper workmanlike manner, using materials and workmanship of the quality specified "
            "in the Contract and in accordance with Good Railway Practice. The Contractor shall comply "
            "with all applicable laws and regulations, including those of the Ministry of Railways, "
            "safety codes, and environmental regulations. The Contractor shall ensure that all its "
            "Subcontractors and suppliers comply with the requirements of this Contract. The Contractor "
            "shall be responsible for the adequacy, stability, and safety of all Site operations and "
            "methods of construction and of all the Works."
        ),
        "risk_category": "LOW",
        "keywords": [
            "general obligations", "workmanship", "Good Railway Practice", "safety", "environment",
            "design", "materials", "compliance", "site operations", "subcontractors"
        ]
    },
    {
        "clause_id": "GCC-2.1",
        "clause_title": "Right of Access to Site",
        "clause_text": (
            "The Employer shall give the Contractor right of access to, and possession of, all parts "
            "of the Site within the time stated in the Contract Data. If no time is stated, the "
            "Employer shall give access and possession as required by the approved programme. If the "
            "Contractor suffers delay and/or incurs Cost as a result of a failure by the Employer to "
            "give right of access or possession within the time specified, the Contractor shall give "
            "notice to the Engineer and shall be entitled to an Extension of Time for any such delay "
            "and payment of any such Cost plus a reasonable profit. The risk of loss or damage to the "
            "Site shall pass to the Contractor from the date on which possession is given. The "
            "Contractor shall not interfere with the convenience of the public or of others while "
            "carrying out work on or near public roads or railways. The Employer shall obtain all "
            "necessary approvals, permissions, and rights-of-way required for the permanent Works."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "site access", "possession", "right of way", "delay", "extension of time",
            "employer obligation", "public road", "railway", "cost plus profit"
        ]
    },
    {
        "clause_id": "GCC-6.1",
        "clause_title": "Labour and Working Conditions",
        "clause_text": (
            "The Contractor shall make its own arrangements for the engagement of all staff and labour, "
            "local or otherwise, and for their payment, housing, feeding, and transport. The Contractor "
            "shall comply with all relevant Labour Laws including: The Minimum Wages Act, 1948; the "
            "Contract Labour (Regulation and Abolition) Act, 1970; the Building and Other Construction "
            "Workers Act, 1996; and the Payment of Wages Act, 1936. The Contractor shall also comply "
            "with all Indian Railways Safety Rules for the protection of workers on and near the "
            "railway tracks. The Contractor shall provide and maintain all necessary welfare facilities "
            "for workers including clean drinking water, sanitary facilities, first aid kits, and "
            "personal protective equipment as required under applicable safety standards. The "
            "Contractor shall not employ children below the age of 14 (fourteen) years and shall "
            "comply with the Prohibition of Child Labour (Prohibition and Regulation) Act. Rates of "
            "wages and conditions of service shall not be less than those prevailing in the locality."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "labour", "working conditions", "Minimum Wages Act", "Contract Labour Act",
            "safety", "welfare", "child labour", "personal protective equipment", "Indian Railways Safety"
        ]
    },
    {
        "clause_id": "GCC-7.1",
        "clause_title": "Plant, Materials and Workmanship Standards",
        "clause_text": (
            "All Plant and Materials shall be new (unless otherwise specified), of the specified "
            "quality, and shall conform to the technical specifications, Indian Standards (IS), "
            "or Indian Railway Standards (IRS) specified in the Contract. The Contractor shall "
            "submit samples, manufacturer's test certificates, and test reports as required by the "
            "Engineer. All Plant and Materials shall be subject to inspection and testing by the "
            "Engineer before being incorporated in the Works. The Employer reserves the right to "
            "reject any Plant or Material that does not conform to the Specification. Testing shall "
            "be carried out at approved laboratories at the Contractor's cost. Materials rejected "
            "by the Engineer shall be immediately removed from the Site. The Contractor shall provide "
            "all facilities required for inspection and testing, including instruments, tools, and "
            "laboratory facilities. Any work incorporating rejected materials shall be demolished "
            "and reconstructed at the Contractor's expense."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "plant", "materials", "workmanship", "Indian Standards", "Indian Railway Standards",
            "IRS", "IS", "inspection", "testing", "rejection", "specification", "laboratory"
        ]
    },
    {
        "clause_id": "GCC-15.1",
        "clause_title": "Taxes and Duties",
        "clause_text": (
            "The Contract Price shall include all taxes, duties, levies, and other fiscal charges "
            "applicable to the Contractor in respect of this Contract, including Goods and Services "
            "Tax (GST), customs duty, import duty, and any other taxes and charges payable under "
            "the laws in force in India. The Contractor shall be responsible for fulfilling all "
            "statutory obligations regarding payment of all taxes and for filing all necessary "
            "tax returns. Any change in applicable tax rates after the Base Date (28 days prior "
            "to the deadline for submission of tenders) shall be taken into account in computing "
            "the Contract Price adjustment. The Employer shall deduct Tax Deducted at Source "
            "(TDS) as required under the Income Tax Act, 1961, from all payments to the Contractor. "
            "GST Input Tax Credit, if any, available to the Employer on account of GST paid by "
            "the Contractor shall be taken into account in the pricing of the Contract."
        ),
        "risk_category": "LOW",
        "keywords": [
            "taxes", "duties", "GST", "customs duty", "TDS", "Income Tax Act",
            "base date", "adjustment", "Goods and Services Tax", "input tax credit"
        ]
    },
    {
        "clause_id": "GCC-16.1",
        "clause_title": "Contractor's Equipment and Temporary Works",
        "clause_text": (
            "The Contractor shall provide all equipment, scaffolding, and temporary structures "
            "required for the execution of the Works. All Contractor's Equipment brought to the "
            "Site shall be deemed to be exclusively intended for the execution of the Works. "
            "The Contractor shall not remove Contractor's Equipment from the Site without the "
            "Engineer's consent, which shall not be unreasonably withheld. The Employer shall "
            "not be liable for loss of or damage to Contractor's Equipment. The Contractor shall "
            "ensure that all Equipment is maintained in a safe and efficient condition throughout "
            "the execution of the Works. Any Contractor's Equipment which, in the opinion of the "
            "Engineer, is unsuitable for the Works shall be removed from the Site. At completion "
            "of the Works, the Contractor shall remove all Equipment and temporary structures "
            "from the Site and shall restore the Site to a condition satisfactory to the Engineer. "
            "Crane and lifting equipment shall be periodically tested and certified as required "
            "by applicable safety laws."
        ),
        "risk_category": "LOW",
        "keywords": [
            "equipment", "temporary works", "scaffolding", "machinery", "removal",
            "site restoration", "Engineer consent", "crane", "lifting equipment", "safety certification"
        ]
    },
    {
        "clause_id": "GCC-17.1",
        "clause_title": "Risk and Responsibility — Care of Works",
        "clause_text": (
            "The Contractor shall take full responsibility for the care of the Works and Goods "
            "from the Commencement Date until the date of issue of the Taking Over Certificate "
            "for the whole of the Works. The Contractor shall indemnify the Employer against "
            "all loss or damage to the Works occurring during this period, except for Employer's "
            "Risks as listed herein. Employer's Risks include: (a) loss or damage caused by war, "
            "hostilities, or similar events; (b) loss or damage caused by ionising radiation; "
            "(c) loss or damage caused by the use or occupation of any part of the Permanent "
            "Works by the Employer after the Taking Over Certificate; (d) loss or damage caused "
            "by the design of the Works by the Employer. If any loss or damage occurs to the Works "
            "due to an Employer's Risk, the Contractor shall rectify the loss or damage as instructed "
            "by the Engineer at the Employer's cost. The Contractor shall bear all risk of loss or "
            "damage caused by any negligent act or omission of the Contractor's Personnel."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "risk", "care of works", "taking over certificate", "employer risk", "indemnity",
            "loss or damage", "negligence", "Contractor Personnel", "ionising radiation"
        ]
    },
    {
        "clause_id": "GCC-3.1",
        "clause_title": "Engineer's Authority and Role",
        "clause_text": (
            "The Employer shall appoint the Engineer to act on its behalf in administering the Contract. "
            "The Engineer shall have authority to act on behalf of the Employer as specified in the Contract. "
            "The Engineer shall give instructions to the Contractor only in accordance with the Contract. "
            "The Contractor shall comply with all instructions given by the Engineer and shall not act "
            "on instructions from any other person except the Engineer or the Engineer's Representative. "
            "The Engineer shall exercise its authority in a fair manner as between the Employer and the "
            "Contractor. The Engineer shall make determinations and exercise discretion fairly. The "
            "Engineer may at any time assign duties and delegate authority to the Engineer's Representative. "
            "The Engineer shall not have authority to amend the Contract Price or the Time for Completion, "
            "which require formal contract amendment executed by both Parties. All instructions, approvals, "
            "or certificates issued by the Engineer shall be in writing."
        ),
        "risk_category": "LOW",
        "keywords": [
            "engineer", "authority", "instruction", "representative", "determination",
            "fairness", "delegation", "contract amendment", "employer", "written instruction"
        ]
    },
    {
        "clause_id": "GCC-10.1",
        "clause_title": "Taking Over of the Works",
        "clause_text": (
            "The Contractor may apply by notice to the Engineer for a Taking Over Certificate for "
            "the Works when the Works are substantially complete, including passing any specified "
            "tests on completion. The Engineer shall, within 28 (twenty-eight) days after receiving "
            "an application: (a) issue the Taking Over Certificate to the Contractor, stating the "
            "date on which the Works were completed in accordance with the Contract, except for "
            "any minor outstanding work and defects which do not substantially affect the use "
            "of the Works; or (b) reject the application, giving reasons. If the Engineer fails "
            "to respond within 28 days, the Engineer shall be deemed to have issued the Taking "
            "Over Certificate on the last day of the 28-day period. The Risk of the Works shall "
            "pass to the Employer from the date stated in the Taking Over Certificate. The "
            "Employer shall not use any part of the Works before the issue of the Taking Over "
            "Certificate unless otherwise agreed. Partial taking over of specific Sections may "
            "be agreed in writing between the Parties."
        ),
        "risk_category": "LOW",
        "keywords": [
            "taking over certificate", "substantial completion", "tests on completion",
            "risk transfer", "minor defects", "partial taking over", "Section", "engineer rejection"
        ]
    },
    {
        "clause_id": "GCC-21.1",
        "clause_title": "Safety and Environmental Management",
        "clause_text": (
            "The Contractor shall comply with all applicable safety regulations and environmental "
            "laws during the execution of the Works, including the Environment Protection Act, 1986, "
            "the Water (Prevention and Control of Pollution) Act, 1974, the Air (Prevention and "
            "Control of Pollution) Act, 1981, and all regulations issued thereunder. The Contractor "
            "shall submit a Safety Management Plan and an Environmental Management Plan to the "
            "Engineer for approval within 14 (fourteen) days of the Commencement Date. All workers "
            "shall be provided with adequate safety training, personal protective equipment, and "
            "emergency first aid. The Contractor shall maintain an Accident Register and report "
            "any fatal or serious accidents to the Engineer and the relevant statutory authorities "
            "within 24 (twenty-four) hours. The Contractor shall take all necessary precautions "
            "to protect the Works, Employer's Property, third parties, and the environment from "
            "pollution, damage, or harm arising from the execution of the Works. "
            "Violations of safety or environmental regulations may result in suspension of Works "
            "and deduction of applicable penalties from payments due."
        ),
        "risk_category": "HIGH",
        "keywords": [
            "safety", "environment", "Environmental Protection Act", "safety plan",
            "accident", "PPE", "pollution", "suspension", "penalties", "statutory compliance"
        ]
    },
    {
        "clause_id": "GCC-12.1",
        "clause_title": "Measurement and Valuation of Works",
        "clause_text": (
            "The Works shall be measured and valued by the Engineer in accordance with the method "
            "of measurement specified in the Contract or, if not specified, in accordance with the "
            "Standard Method of Measurement published by the Institution of Civil Engineers or the "
            "Indian Railways Schedule of Rates. Unless otherwise stated in the Contract, all "
            "measurements shall be of the net actual quantities of each item of permanent work "
            "as constructed. The Engineer shall give the Contractor not less than 7 (seven) days' "
            "notice before taking any measurement so that the Contractor may arrange for its "
            "Representative to be present. If the Contractor does not attend, the measurement "
            "taken by the Engineer shall be binding on the Contractor. The Contractor shall "
            "provide all assistance required by the Engineer for measurement including instruments, "
            "survey equipment, labour, and measurement records. Where unit rates are included in "
            "the Bill of Quantities, the Work shall be measured and valued using those rates. "
            "New rates shall be derived by agreement where the Engineer orders work not covered "
            "by the Bill of Quantities."
        ),
        "risk_category": "LOW",
        "keywords": [
            "measurement", "valuation", "Bill of Quantities", "Schedule of Rates",
            "Engineer", "representative", "unit rates", "new rates", "survey", "permanent work"
        ]
    },
    {
        "clause_id": "GCC-9.1",
        "clause_title": "Tests on Completion",
        "clause_text": (
            "The Contractor shall carry out the specified Tests on Completion after providing the "
            "documents required under the Contract, including as-built drawings and operation and "
            "maintenance manuals. The Contractor shall give 21 (twenty-one) days' notice to the "
            "Engineer of the date on which it intends to carry out each Test on Completion. "
            "The Engineer or the Engineer's Representative shall attend the tests. If the "
            "Contractor is unavailable to attend on the specified date, the Engineer may proceed "
            "with the test in the Contractor's absence and the test results shall be binding. "
            "If any Tests on Completion are being unduly delayed by the Employer, the Contractor "
            "may give notice requiring the Employer to permit the tests within 21 days, failing "
            "which the Contractor may proceed with the tests in the Employer's absence. If the "
            "Works fail any Test on Completion, the Engineer shall specify the remedial work "
            "to be done. After completing the remedial work, the test shall be repeated at the "
            "Contractor's cost. If the Works repeatedly fail, the Employer may reject the Works, "
            "terminate the relevant part of the Contract, and recover all costs from the Contractor."
        ),
        "risk_category": "MEDIUM",
        "keywords": [
            "tests on completion", "commissioning", "as-built drawings", "operation manual",
            "notice", "Engineer", "remedial work", "rejection", "repeated failure", "termination"
        ]
    },
]
