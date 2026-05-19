# Generated transformation review checklist

## Contract alignment

- [ ] Dataset id matches contract
- [ ] Input columns are handled correctly
- [ ] Target columns match contract
- [ ] Data types are respected
- [ ] Required lookup joins are implemented

## Code quality

- [ ] No hardcoded storage account names
- [ ] No secrets
- [ ] No environment-specific paths
- [ ] Function is modular and testable
- [ ] Error handling is clear
- [ ] No runtime LLM calls

## Testing

- [ ] Unit tests exist
- [ ] Schema test exists
- [ ] Key transformation tests exist
- [ ] Invalid input tests exist
- [ ] Tests use synthetic/sample data only

## Governance

- [ ] PII handling reviewed if applicable
- [ ] DQ suggestions reviewed if applicable
- [ ] Lineage impact understood
- [ ] Human reviewer assigned

## Approval

- [ ] Approved
- [ ] Rejected
- [ ] Requires changes
