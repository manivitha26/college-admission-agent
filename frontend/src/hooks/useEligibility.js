/**
 * hooks/useEligibility.js
 * Manages all state for the eligibility checker form.
 *
 * Returned values
 * ---------------
 * fields        – controlled form values
 * setField      – update one field by name
 * isLoading     – true while waiting for the backend
 * result        – { analysis, disclaimer, sources } or null
 * error         – error string or null
 * submit()      – validates locally then calls POST /api/eligibility
 * reset()       – clears result and error
 */

import { useState, useCallback } from "react";
import { checkEligibility } from "../api/client";

const INITIAL_FIELDS = {
  percentage_12th:  "",
  maths_marks:      "",
  physics_marks:    "",
  chemistry_marks:  "",
  preferred_course: "",
};

export function useEligibility() {
  const [fields,    setFields]    = useState(INITIAL_FIELDS);
  const [isLoading, setIsLoading] = useState(false);
  const [result,    setResult]    = useState(null);   // EligibilityResponse
  const [error,     setError]     = useState(null);   // string

  // Update a single field value.
  const setField = useCallback((name, value) => {
    setFields((prev) => ({ ...prev, [name]: value }));
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  const submit = useCallback(async () => {
    // ── Local validation ────────────────────────────────────────
    const pct    = parseFloat(fields.percentage_12th);
    const maths  = parseFloat(fields.maths_marks);
    const phy    = parseFloat(fields.physics_marks);
    const chem   = parseFloat(fields.chemistry_marks);
    const course = fields.preferred_course.trim();

    const inRange = (n) => !isNaN(n) && n >= 0 && n <= 100;

    if (!inRange(pct))   return setError("Please enter a valid 12th percentage (0–100).");
    if (!inRange(maths)) return setError("Please enter valid Mathematics marks (0–100).");
    if (!inRange(phy))   return setError("Please enter valid Physics marks (0–100).");
    if (!inRange(chem))  return setError("Please enter valid Chemistry marks (0–100).");
    if (!course)         return setError("Please enter your preferred course.");

    setError(null);
    setResult(null);
    setIsLoading(true);

    try {
      const data = await checkEligibility({
        percentage_12th:  pct,
        maths_marks:      maths,
        physics_marks:    phy,
        chemistry_marks:  chem,
        preferred_course: course,
      });
      setResult(data);
    } catch (err) {
      setError(
        err?.response?.data?.detail ??
        err?.message ??
        "Something went wrong. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  }, [fields]);

  return { fields, setField, isLoading, result, error, submit, reset };
}
