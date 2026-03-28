# REVIEW.md

## Before Accepting Code

### Must Pass

* Compiles without errors
* Matches function signatures
* Follows architecture rules

---

### Tools

* Return string
* No exceptions
* Flush after writes

---

### Environment

* step() always returns Observation
* reward computed correctly
* done condition correct

---

### Determinism

* no randomness
* consistent outputs

---

## Reject If

* breaks architecture
* introduces hidden state
* violates OpenEnv contract
