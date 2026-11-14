# Human check: eu.yaml (20 entries, about 15 minutes)

Rule at the top of `eu.yaml`: `verified: true` only after a human has opened `official_url` and confirmed ref + summary. So far only an AI agent has done that.

For each line: open the document link, search (Ctrl/Cmd+F) for the quoted words, and tick the box if all three hold:

1. the words are on the page,
2. they sit under the article named on the line,
3. the `summary` for that id in `eu.yaml` says no more than the text does.

If one fails, leave the box empty and write why next to it. Unticked entries go back to `verified: false`.

Checked by: ________  Date: ________

If EUR-Lex shows "temporarily not fully available" (it did on 14 November 2026), use the Publications Office copy given after each link. It is the same document.

## A. GDPR, Regulation (EU) 2016/679 (14 entries)

https://eur-lex.europa.eu/eli/reg/2016/679/oj (copy: https://publications.europa.eu/resource/celex/32016R0679)

The articles start after 173 recitals. Check that each hit is in the article, not in a recital. Arts. 13 and 14 share most of their wording; the hits for Art. 13 must be under Article 13.

- [ ] `EU-GDPR-5-1-a` Art. 5(1)(a): "processed lawfully, fairly and in a transparent manner in relation to the data subject"
- [ ] `EU-GDPR-5-1-e` Art. 5(1)(e): "kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed"
- [ ] `EU-GDPR-5-1-f` Art. 5(1)(f): "processed in a manner that ensures appropriate security of the personal data, including protection against unauthorised or unlawful processing"
- [ ] `EU-GDPR-6` Art. 6(1): "Processing shall be lawful only if and to the extent that at least one of the following applies"
- [ ] `EU-GDPR-7` Art. 7(1) and 7(3): "the controller shall be able to demonstrate that the data subject has consented" and "It shall be as easy to withdraw as to give consent."
- [ ] `EU-GDPR-13-1-c` Art. 13(1)(c): "the purposes of the processing for which the personal data are intended as well as the legal basis for the processing"
- [ ] `EU-GDPR-13-1-e` Art. 13(1)(e): "the recipients or categories of recipients of the personal data, if any"
- [ ] `EU-GDPR-13-1-f` Art. 13(1)(f): "the fact that the controller intends to transfer personal data to a third country or international organisation"
- [ ] `EU-GDPR-13-2-a` Art. 13(2)(a): "the period for which the personal data will be stored, or if that is not possible, the criteria used to determine that period"
- [ ] `EU-GDPR-13-2-b` Art. 13(2)(b): "the existence of the right to request from the controller access to and rectification or erasure of personal data"
- [ ] `EU-GDPR-17` Art. 17(1): "the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"
- [ ] `EU-GDPR-22` Art. 22(1): "the right not to be subject to a decision based solely on automated processing, including profiling"
- [ ] `EU-GDPR-28` Art. 28(1) and 28(3): "the controller shall use only processors providing sufficient guarantees" and "sets out the subject-matter and duration of the processing, the nature and purpose of the processing"
- [ ] `EU-GDPR-44` Art. 44: "shall take place only if, subject to the other provisions of this Regulation, the conditions laid down in this Chapter are complied with"

## B. ePrivacy Directive 2002/58/EC, consolidated 19.12.2009 (1 entry, now `verified: false`)

https://eur-lex.europa.eu/eli/dir/2002/58/2009-12-19 (copy: https://publications.europa.eu/resource/celex/02002L0058-20091219)

This entry was corrected in #17: the link used to open the 2002 text, which has no consent requirement. Confirm the page is the consolidated version (paragraph 3 carries the marker M2). A tick here flips the entry to `verified: true`.

- [ ] `EU-EPRIVACY-5-3` Art. 5(3): "is only allowed on condition that the subscriber or user concerned has given his or her consent, having been provided with clear and comprehensive information" and "as strictly necessary in order for the provider of an information society service explicitly requested by the subscriber or user to provide the service"

## C. AI Act, Regulation (EU) 2024/1689 (2 entries)

https://eur-lex.europa.eu/eli/reg/2024/1689/oj (copy: https://publications.europa.eu/resource/celex/32024R1689)

- [ ] `EU-AIACT-50-1` Art. 50(1): "the natural persons concerned are informed that they are interacting with an AI system"
- [ ] `EU-AIACT-50-2` Art. 50(2): "the outputs of the AI system are marked in a machine-readable format and detectable as artificially generated or manipulated"

## D. Unfair Commercial Practices Directive 2005/29/EC (3 entries)

https://eur-lex.europa.eu/eli/dir/2005/29/oj (copy: https://publications.europa.eu/resource/celex/32005L0029)

The link opens the 2005 text. The directive has been amended since; the three quotes below are also in the consolidated version of 28.05.2022.

- [ ] `EU-UCPD-5` Art. 5(1) and 5(2)(b): "Unfair commercial practices shall be prohibited." and "it materially distorts or is likely to materially distort the economic behaviour"
- [ ] `EU-UCPD-6` Art. 6(1): "contains false information and is therefore untruthful or in any way, including overall presentation, deceives or is likely to deceive the average consumer"
- [ ] `EU-UCPD-7` Art. 7(1): "it omits material information that the average consumer needs, according to the context, to take an informed transactional decision"
