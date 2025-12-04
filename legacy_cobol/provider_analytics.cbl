       IDENTIFICATION DIVISION.
       PROGRAM-ID. PROVIDER-PERFORMANCE.
       AUTHOR. NETWORK-MANAGEMENT-TEAM.
       DATE-WRITTEN. 07/22/2023.
       
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT PROVIDER-FILE
               ASSIGN TO "PROVIDERS.DAT"
               ORGANIZATION IS LINE SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL.
           SELECT CLAIM-FILE
               ASSIGN TO "CLAIMS.DAT"
               ORGANIZATION IS LINE SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL.
       
       DATA DIVISION.
       FILE SECTION.
       FD  PROVIDER-FILE.
       01  PROVIDER-RECORD.
           05  PROVIDER-ID         PIC 9(8).
           05  PROVIDER-NAME       PIC X(50).
           05  PROVIDER-TYPE       PIC X(20).
           05  SPECIALTY           PIC X(30).
           05  NETWORK-STATUS      PIC X(10).
           05  CONTRACT-RATE       PIC 9(3)V99.
       
       FD  CLAIM-FILE.
       01  CLAIM-RECORD.
           05  CLAIM-ID            PIC 9(12).
           05  MEMBER-ID           PIC 9(10).
           05  PROVIDER-ID         PIC 9(8).
           05  SERVICE-DATE        PIC 9(8).
           05  CLAIM-AMOUNT        PIC 9(7)V99 COMP-3.
           05  PAID-AMOUNT         PIC 9(7)V99 COMP-3.
           05  CLAIM-STATUS        PIC X(10).
           05  QUALITY-SCORE       PIC 9(3).
       
       WORKING-STORAGE SECTION.
       01  WS-PROVIDER-METRICS.
           05  WS-CLAIM-COUNT      PIC 9(7) VALUE ZERO.
           05  WS-TOTAL-CHARGES    PIC 9(11)V99 VALUE ZERO.
           05  WS-TOTAL-PAID       PIC 9(11)V99 VALUE ZERO.
           05  WS-AVG-CLAIM-AMT    PIC 9(7)V99.
           05  WS-AVG-QUALITY      PIC 9(3)V99.
           05  WS-APPROVAL-RATE    PIC 9(3)V99.
       
       01  WS-PERFORMANCE-TIER     PIC X(15).
       01  WS-EFFICIENCY-SCORE     PIC 9(3).
       
       01  WS-FLAGS.
           05  EOF-PROVIDER        PIC X VALUE 'N'.
               88  END-OF-PROVIDERS VALUE 'Y'.
           05  EOF-CLAIM           PIC X VALUE 'N'.
               88  END-OF-CLAIMS   VALUE 'Y'.
       
       01  WS-CURRENT-PROVIDER     PIC 9(8).
       01  WS-ANALYSIS-YEAR        PIC 9(4) VALUE 2023.
       01  WS-APPROVED-COUNT       PIC 9(7) VALUE ZERO.
       
       PROCEDURE DIVISION.
       MAIN-LOGIC.
           PERFORM OPEN-FILES
           PERFORM PROCESS-ALL-PROVIDERS
           PERFORM CLOSE-FILES
           STOP RUN.
       
       OPEN-FILES.
      *    Open input files from mainframe
      *    Source: PAYER-DEV.ANALYTICS-GOLD.PROVIDERS
      *    Source: PAYER-DEV.ANALYTICS-GOLD.CLAIMS
           OPEN INPUT PROVIDER-FILE
           OPEN INPUT CLAIM-FILE
           READ PROVIDER-FILE
               AT END SET END-OF-PROVIDERS TO TRUE
           END-READ
           READ CLAIM-FILE
               AT END SET END-OF-CLAIMS TO TRUE
           END-READ.
       
       PROCESS-ALL-PROVIDERS.
      *    Calculate performance metrics for each provider
           PERFORM UNTIL END-OF-PROVIDERS
               MOVE PROVIDER-ID TO WS-CURRENT-PROVIDER
               PERFORM INITIALIZE-METRICS
               PERFORM PROCESS-PROVIDER-CLAIMS
               PERFORM CALCULATE-METRICS
               PERFORM CLASSIFY-PERFORMANCE
               PERFORM WRITE-PROVIDER-REPORT
               
               READ PROVIDER-FILE
                   AT END SET END-OF-PROVIDERS TO TRUE
               END-READ
           END-PERFORM.
       
       INITIALIZE-METRICS.
      *    Initialize metrics for provider
           MOVE ZERO TO WS-CLAIM-COUNT
           MOVE ZERO TO WS-TOTAL-CHARGES
           MOVE ZERO TO WS-TOTAL-PAID
           MOVE ZERO TO WS-APPROVED-COUNT
           MOVE ZERO TO WS-AVG-QUALITY.
       
       PROCESS-PROVIDER-CLAIMS.
      *    Process all claims for current provider
           PERFORM UNTIL END-OF-CLAIMS OR
                        PROVIDER-ID NOT = WS-CURRENT-PROVIDER
               ADD 1 TO WS-CLAIM-COUNT
               ADD CLAIM-AMOUNT TO WS-TOTAL-CHARGES
               ADD PAID-AMOUNT TO WS-TOTAL-PAID
               
               IF CLAIM-STATUS = 'APPROVED' OR
                  CLAIM-STATUS = 'PARTIAL'
                   ADD 1 TO WS-APPROVED-COUNT
               END-IF
               
               ADD QUALITY-SCORE TO WS-AVG-QUALITY
               
               READ CLAIM-FILE
                   AT END SET END-OF-CLAIMS TO TRUE
               END-READ
           END-PERFORM.
       
       CALCULATE-METRICS.
      *    Calculate summary metrics
           IF WS-CLAIM-COUNT > 0
               COMPUTE WS-AVG-CLAIM-AMT = 
                   WS-TOTAL-CHARGES / WS-CLAIM-COUNT
               COMPUTE WS-AVG-QUALITY = 
                   WS-AVG-QUALITY / WS-CLAIM-COUNT
               COMPUTE WS-APPROVAL-RATE = 
                   (WS-APPROVED-COUNT / WS-CLAIM-COUNT) * 100
           END-IF.
       
       CLASSIFY-PERFORMANCE.
      *    Classify provider performance tier
           MOVE ZERO TO WS-EFFICIENCY-SCORE.
           
      *    Quality component (40%)
           IF WS-AVG-QUALITY >= 90
               ADD 40 TO WS-EFFICIENCY-SCORE
           ELSE IF WS-AVG-QUALITY >= 80
               ADD 30 TO WS-EFFICIENCY-SCORE
           ELSE IF WS-AVG-QUALITY >= 70
               ADD 20 TO WS-EFFICIENCY-SCORE
           ELSE
               ADD 10 TO WS-EFFICIENCY-SCORE
           END-IF.
           
      *    Approval rate component (30%)
           IF WS-APPROVAL-RATE >= 95
               ADD 30 TO WS-EFFICIENCY-SCORE
           ELSE IF WS-APPROVAL-RATE >= 90
               ADD 25 TO WS-EFFICIENCY-SCORE
           ELSE IF WS-APPROVAL-RATE >= 85
               ADD 20 TO WS-EFFICIENCY-SCORE
           ELSE
               ADD 10 TO WS-EFFICIENCY-SCORE
           END-IF.
           
      *    Cost efficiency component (30%)
           IF WS-AVG-CLAIM-AMT < 200
               ADD 30 TO WS-EFFICIENCY-SCORE
           ELSE IF WS-AVG-CLAIM-AMT < 500
               ADD 20 TO WS-EFFICIENCY-SCORE
           ELSE IF WS-AVG-CLAIM-AMT < 1000
               ADD 15 TO WS-EFFICIENCY-SCORE
           ELSE
               ADD 10 TO WS-EFFICIENCY-SCORE
           END-IF.
           
      *    Classify tier based on total score
           EVALUATE TRUE
               WHEN WS-EFFICIENCY-SCORE >= 90
                   MOVE 'TIER 1' TO WS-PERFORMANCE-TIER
               WHEN WS-EFFICIENCY-SCORE >= 75
                   MOVE 'TIER 2' TO WS-PERFORMANCE-TIER
               WHEN WS-EFFICIENCY-SCORE >= 60
                   MOVE 'TIER 3' TO WS-PERFORMANCE-TIER
               WHEN OTHER
                   MOVE 'NEEDS IMPROVEMENT' TO WS-PERFORMANCE-TIER
           END-EVALUATE.
       
       WRITE-PROVIDER-REPORT.
      *    Write provider performance metrics
      *    Target: PAYER-ANALYST.PROVIDER-ANALYTICS.PERFORMANCE
           DISPLAY '=========================================='
           DISPLAY 'PROVIDER PERFORMANCE REPORT'
           DISPLAY 'PROVIDER ID: ' WS-CURRENT-PROVIDER
           DISPLAY 'PROVIDER NAME: ' PROVIDER-NAME
           DISPLAY 'SPECIALTY: ' SPECIALTY
           DISPLAY '=========================================='
           DISPLAY ' '
           DISPLAY 'CLAIMS METRICS:'
           DISPLAY '  Total Claims: ' WS-CLAIM-COUNT
           DISPLAY '  Approved Claims: ' WS-APPROVED-COUNT
           DISPLAY '  Approval Rate: ' WS-APPROVAL-RATE '%'
           DISPLAY ' '
           DISPLAY 'FINANCIAL METRICS:'
           DISPLAY '  Total Charges: $' WS-TOTAL-CHARGES
           DISPLAY '  Total Paid: $' WS-TOTAL-PAID
           DISPLAY '  Average Claim: $' WS-AVG-CLAIM-AMT
           DISPLAY ' '
           DISPLAY 'QUALITY METRICS:'
           DISPLAY '  Average Quality Score: ' WS-AVG-QUALITY
           DISPLAY '  Efficiency Score: ' WS-EFFICIENCY-SCORE
           DISPLAY '  Performance Tier: ' WS-PERFORMANCE-TIER
           DISPLAY '=========================================='
           DISPLAY ' '.
       
       CLOSE-FILES.
           CLOSE PROVIDER-FILE
           CLOSE CLAIM-FILE.


