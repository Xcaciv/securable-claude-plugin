# PRD: Internal Performance Review Browser

## Context

Internal-only tool for HR staff to view and comment on employee performance reviews. Hosted on the corporate intranet behind SSO. Used by ~80 HR staff across 4 regions. Performance review data includes manager comments, ratings, compensation notes, and free-text peer feedback.

## Features

### F-01: View employee performance review

HR staff can search for an employee by name or employee ID and open their performance review history. The page shows all past reviews in reverse chronological order with reviewer, date, rating, manager comment, and any peer feedback.

### F-02: Add HR commentary

HR staff can attach a private commentary note to an existing review. The note is visible to other HR staff but not to the employee or their manager. Notes are timestamped with the author's name.

### F-03: Export region report

HR staff can export a CSV of all reviews in their region for the current cycle. The CSV includes employee ID, name, rating, manager comment, and compensation note.

### F-04: Bulk reassign reviewer

When a manager leaves the company, an HR admin can bulk-reassign all of that manager's pending reviews to another manager. The admin selects the source and target managers and clicks "Reassign all".

## Out of Scope

- Mobile app
- Self-service access by employees (separate product)
- Integration with payroll systems

## Acceptance

- HR staff can complete each task without raising a support ticket.
- The tool loads in under 2 seconds for typical queries.
