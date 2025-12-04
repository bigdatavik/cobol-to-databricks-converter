       IDENTIFICATION DIVISION.
       PROGRAM-ID. CLAIMS-COST-ANALYSIS.
       AUTHOR. ACTUARIAL-TEAM.
       DATE-WRITTEN. 09/20/2023.
       
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT CLAIM-FILE
               ASSIGN TO "CLAIMS.DAT"
               ORGANIZATION IS LINE SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL.
       
       DATA DIVISION.
       FILE SECTION.
       FD  CLAIM-FILE.
       01  CLAIM-RECORD.
           05  CLAIM-ID            PIC 9(12).
           05  MEMBER-ID           PIC 9(10).
           05  PROVIDER-ID         PIC 9(8).
           05  SERVICE-DATE        PIC 9(8).
           05  CLAIM-TYPE          PIC X(10).
           05  PROCEDURE-CODE      PIC X(5).
           05  DIAGNOSIS-CODE      PIC X(7).
           05  CLAIM-AMOUNT        PIC 9(7)V99 COMP-3.
           05  PAID-AMOUNT         PIC 9(7)V99 COMP-3.
           05  DENIED-AMOUNT       PIC 9(7)V99 COMP-3.
           05  CLAIM-STATUS        PIC X(10).
       
       WORKING-STORAGE SECTION.
       01  WS-COUNTERS.
           05  WS-TOTAL-CLAIMS     PIC 9(9) VALUE ZERO.
           05  WS-APPROVED-CLAIMS  PIC 9(9) VALUE ZERO.
           05  WS-DENIED-CLAIMS    PIC 9(9) VALUE ZERO.
           05  WS-HIGH-COST-COUNT  PIC 9(9) VALUE ZERO.
       
       01  WS-AMOUNTS.
           05  WS-TOTAL-BILLED     PIC 9(11)V99 COMP-3 VALUE ZERO.
           05  WS-TOTAL-PAID       PIC 9(11)V99 COMP-3 VALUE ZERO.
           05  WS-TOTAL-DENIED     PIC 9(11)V99 COMP-3 VALUE ZERO.
           05  WS-AVG-CLAIM        PIC 9(7)V99.
           05  WS-AVG-PAID         PIC 9(7)V99.
       
       01  WS-THRESHOLDS.
           05  WS-HIGH-COST-LIMIT  PIC 9(7)V99 VALUE 50000.00.
       
       01  WS-PERCENTAGES.
           05  WS-APPROVAL-RATE    PIC 9(3)V99.
           05  WS-DENIAL-RATE      PIC 9(3)V99.
           05  WS-PAID-PCT         PIC 9(3)V99.
       
       01  WS-FLAGS.
           05  EOF-FLAG            PIC X VALUE 'N'.
               88  END-OF-FILE     VALUE 'Y'.
       
       01  WS-ANALYSIS-YEAR        PIC 9(4) VALUE 2023.
       01  WS-RISK-LEVEL           PIC X(10).
       
       PROCEDURE DIVISION.
       MAIN-LOGIC.
           PERFORM OPEN-FILES
           PERFORM PROCESS-CLAIMS
           PERFORM CALCULATE-METRICS
           PERFORM WRITE-ANALYSIS-REPORT
           PERFORM CLOSE-FILES
           STOP RUN.
       
       OPEN-FILES.
      *    Open input file from mainframe
      *    Source: PAYER-DEV.ANALYTICS-GOLD.CLAIMS
           OPEN INPUT CLAIM-FILE
           READ CLAIM-FILE
               AT END SET END-OF-FILE TO TRUE
           END-READ.
       
       PROCESS-CLAIMS.
      *    Process all claims and accumulate statistics
           PERFORM UNTIL END-OF-FILE
               ADD 1 TO WS-TOTAL-CLAIMS
               ADD CLAIM-AMOUNT TO WS-TOTAL-BILLED
               
               PERFORM ANALYZE-CLAIM-STATUS
               PERFORM CHECK-HIGH-COST-CLAIM
               
               READ CLAIM-FILE
                   AT END SET END-OF-FILE TO TRUE
               END-READ
           END-PERFORM.
       
       ANALYZE-CLAIM-STATUS.
      *    Categorize claims by status
           EVALUATE CLAIM-STATUS
               WHEN 'APPROVED'
                   ADD 1 TO WS-APPROVED-CLAIMS
                   ADD PAID-AMOUNT TO WS-TOTAL-PAID
               WHEN 'DENIED'
                   ADD 1 TO WS-DENIED-CLAIMS
                   ADD DENIED-AMOUNT TO WS-TOTAL-DENIED
               WHEN 'PARTIAL'
                   ADD 1 TO WS-APPROVED-CLAIMS
                   ADD PAID-AMOUNT TO WS-TOTAL-PAID
                   ADD DENIED-AMOUNT TO WS-TOTAL-DENIED
           END-EVALUATE.
       
       CHECK-HIGH-COST-CLAIM.
      *    Identify high-cost claims for review
           IF CLAIM-AMOUNT > WS-HIGH-COST-LIMIT
               ADD 1 TO WS-HIGH-COST-COUNT
               PERFORM CLASSIFY-RISK-LEVEL
           END-IF.
       
       CLASSIFY-RISK-LEVEL.
      *    Classify claims by risk level
           EVALUATE TRUE
               WHEN CLAIM-AMOUNT > 100000
                   MOVE 'CRITICAL' TO WS-RISK-LEVEL
               WHEN CLAIM-AMOUNT > 50000
                   MOVE 'HIGH' TO WS-RISK-LEVEL
               WHEN CLAIM-AMOUNT > 10000
                   MOVE 'MEDIUM' TO WS-RISK-LEVEL
               WHEN OTHER
                   MOVE 'LOW' TO WS-RISK-LEVEL
           END-EVALUATE.
       
       CALCULATE-METRICS.
      *    Calculate summary metrics
           IF WS-TOTAL-CLAIMS > 0
               COMPUTE WS-AVG-CLAIM = 
                   WS-TOTAL-BILLED / WS-TOTAL-CLAIMS
               COMPUTE WS-AVG-PAID = 
                   WS-TOTAL-PAID / WS-APPROVED-CLAIMS
               COMPUTE WS-APPROVAL-RATE = 
                   (WS-APPROVED-CLAIMS / WS-TOTAL-CLAIMS) * 100
               COMPUTE WS-DENIAL-RATE = 
                   (WS-DENIED-CLAIMS / WS-TOTAL-CLAIMS) * 100
               COMPUTE WS-PAID-PCT = 
                   (WS-TOTAL-PAID / WS-TOTAL-BILLED) * 100
           END-IF.
       
       WRITE-ANALYSIS-REPORT.
      *    Write output to: PAYER-ANALYST.CLAIMS-ANALYSIS.COST-SUMMARY
           DISPLAY '=========================================='
           DISPLAY 'CLAIMS COST ANALYSIS REPORT'
           DISPLAY 'ANALYSIS YEAR: ' WS-ANALYSIS-YEAR
           DISPLAY '=========================================='
           DISPLAY ' '
           DISPLAY 'CLAIMS VOLUME:'
           DISPLAY '  Total Claims: ' WS-TOTAL-CLAIMS
           DISPLAY '  Approved: ' WS-APPROVED-CLAIMS
           DISPLAY '  Denied: ' WS-DENIED-CLAIMS
           DISPLAY '  High-Cost (>$50K): ' WS-HIGH-COST-COUNT
           DISPLAY ' '
           DISPLAY 'FINANCIAL SUMMARY:'
           DISPLAY '  Total Billed: $' WS-TOTAL-BILLED
           DISPLAY '  Total Paid: $' WS-TOTAL-PAID
           DISPLAY '  Total Denied: $' WS-TOTAL-DENIED
           DISPLAY '  Average Claim: $' WS-AVG-CLAIM
           DISPLAY '  Average Paid: $' WS-AVG-PAID
           DISPLAY ' '
           DISPLAY 'PERFORMANCE METRICS:'
           DISPLAY '  Approval Rate: ' WS-APPROVAL-RATE '%'
           DISPLAY '  Denial Rate: ' WS-DENIAL-RATE '%'
           DISPLAY '  Paid Percentage: ' WS-PAID-PCT '%'
           DISPLAY '=========================================='
           DISPLAY 'ANALYSIS COMPLETE'.
       
       CLOSE-FILES.
           CLOSE CLAIM-FILE.


