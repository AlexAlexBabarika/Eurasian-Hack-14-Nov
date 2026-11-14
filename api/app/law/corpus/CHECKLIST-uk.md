# Human check: uk.yaml (20 entries, about 15 minutes)

Rule at the top of `uk.yaml`: `verified: true` only after a human has opened `official_url` and confirmed ref + summary. So far only an AI agent has done that.

For each line: open the link, search (Ctrl/Cmd+F) for the quoted words, and tick the box if all three hold:

1. the words are on the page,
2. they sit under the article, section or paragraph named on the line,
3. the `summary` for that id in `uk.yaml` says no more than the text does.

If one fails, leave the box empty and write why next to it. Unticked entries go back to `verified: false`.

Checked by: ________  Date: ________

On legislation.gov.uk keep "Latest available (Revised)" selected. Text in square brackets with an F number is an amendment; the note under the article says what made it and when.

## A. UK GDPR (13 entries, 10 pages)

- [ ] `UK-GDPR-5-1-a` Art. 5(1)(a), https://www.legislation.gov.uk/eur/2016/679/article/5 : "processed lawfully, fairly and in a transparent manner in relation to the data subject"
- [ ] `UK-GDPR-5-1-e` Art. 5(1)(e), same page: "kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed"
- [ ] `UK-GDPR-5-1-f` Art. 5(1)(f), same page: "processed in a manner that ensures appropriate security of the personal data, including protection against unauthorised or unlawful processing"
- [ ] `UK-GDPR-6` Art. 6(1), https://www.legislation.gov.uk/eur/2016/679/article/6 : "Processing shall be lawful only if and to the extent that at least one of the following applies"
- [ ] `UK-GDPR-7` Art. 7(1) and 7(3), https://www.legislation.gov.uk/eur/2016/679/article/7 : "the controller shall be able to demonstrate that the data subject has consented" and "It shall be as easy to withdraw as to give consent."
- [ ] `UK-GDPR-13-1-c` Art. 13(1)(c), https://www.legislation.gov.uk/eur/2016/679/article/13 : "the purposes of the processing for which the personal data are intended as well as the legal basis for the processing"
- [ ] `UK-GDPR-13-1-e` Art. 13(1)(e), same page: "the recipients or categories of recipients of the personal data, if any"
- [ ] `UK-GDPR-13-1-f` Art. 13(1)(f), same page: "the fact that the controller intends to transfer personal data to a third country or international organisation" and "the safeguards relied on"
- [ ] `UK-GDPR-13-2-a` Art. 13(2)(a), same page: "the period for which the personal data will be stored, or if that is not possible, the criteria used to determine that period"
- [ ] `UK-GDPR-17` Art. 17(1), https://www.legislation.gov.uk/eur/2016/679/article/17 : "the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"
- [ ] `UK-GDPR-28` Art. 28(1) and 28(3), https://www.legislation.gov.uk/eur/2016/679/article/28 : "the controller shall use only processors providing sufficient guarantees" and "that sets out the subject-matter and duration of the processing"

Two corrected entries, now `verified: false`. A tick flips the entry to `verified: true`.

- [ ] `UK-GDPR-22` Arts. 22A-22C (three pages):
  - https://www.legislation.gov.uk/eur/2016/679/article/22C : "enable the data subject to obtain human intervention on the part of the controller", and in the note under the article "19.6.2025 for specified purposes, 5.2.2026 in so far as not already in force"
  - https://www.legislation.gov.uk/eur/2016/679/article/22A : "there is no meaningful human involvement in the taking of the decision"
  - https://www.legislation.gov.uk/eur/2016/679/article/22B : "may not be taken based solely on automated processing, unless one of the following conditions is met"
- [ ] `UK-GDPR-44A` Art. 44A, https://www.legislation.gov.uk/eur/2016/679/article/44A : "A controller or processor may transfer personal data to a third country or an international organisation only if" and "is approved by regulations under Article 45A"

## B. Data Protection Act 2018 (1 entry, now `verified: false`)

A tick flips the entry to `verified: true`. The summary says Part 2 supplements the UK GDPR and includes exemptions; the link is the contents page, so the wording is one click away in section 4.

- [ ] `UK-DPA-2018` Part 2:
  - https://www.legislation.gov.uk/ukpga/2018/12/contents : "PART 2 General processing" and, inside Part 2, "Exemptions etc"
  - https://www.legislation.gov.uk/ukpga/2018/12/section/4 : "supplements, and must be read with, the"

## C. PECR, cookies (2 entries; links changed in the follow-up to #17)

Both links now open the regulations themselves instead of the amending Act. These are the cells the demo opens.

- [ ] `UK-PECR-6` reg. 6(1), https://www.legislation.gov.uk/uksi/2003/2426/regulation/6 : "a person must not store information, or gain access to information stored, in the terminal equipment of a subscriber or user", and in the note "Reg. 6 substituted (5.2.2026) by"
- [ ] `UK-PECR-SCHA1-5` Sch. A1 para. 5, https://www.legislation.gov.uk/uksi/2003/2426/schedule/A1 : "to collect information for statistical purposes about how the service is used with a view to making improvements to the service", "is not shared with any other person except for the purpose of enabling that other person to assist with making improvements" and "is given a simple means of objecting, free of charge, to the storage or access and does not object"

## D. ICO guidance (1 entry)

- [ ] `UK-ICO-AI-GUIDANCE` "How do we ensure transparency in AI?", https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/artificial-intelligence/guidance-on-ai-and-data-protection/how-do-we-ensure-transparency-in-ai/ : "You need to be transparent about how you process personal data in an AI system, to comply with the principle of transparency."

The page carries a banner saying the guidance is under review because of the Data (Use and Access) Act. The summary's first sentence, "The UK has no AI-specific statute", is not on this page; it is our context, so decide whether it should stay.

## E. Digital Markets, Competition and Consumers Act 2024 (3 entries)

- [ ] `UK-DMCC-225` s. 225(1) and 225(4), https://www.legislation.gov.uk/ukpga/2024/13/section/225 : "Unfair commercial practices are prohibited." and "a misleading action (see section 226)"
- [ ] `UK-DMCC-226` s. 226(1), https://www.legislation.gov.uk/ukpga/2024/13/section/226 : "the provision of false or misleading information relating to a product, a trader or any other matter relevant to a transactional decision"
- [ ] `UK-DMCC-227` s. 227(1)-(2), https://www.legislation.gov.uk/ukpga/2024/13/section/227 : "omits material information" and "information that the average consumer needs to take an informed transactional decision"
