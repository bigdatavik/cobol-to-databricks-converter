       IDENTIFICATION DIVISION.
       PROGRAM-ID. PRIOR-AUTH-TURNAROUND.
       AUTHOR. UTILIZATION-MANAGEMENT-TEAM.
       DATE-WRITTEN. 06/15/2023.
       
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT PRIOR-AUTH-FILE
               ASSIGN TO "PRIOR-AUTH.DAT"
               ORGANIZATION IS LINE SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL.
       
       DATA DIVISION.
       FILE SECTION.
       FD  PRIOR-AUTH-FILE.
       01  PRIOR-AUTH-RECORD.
           05  AUTH-ID             PIC 9(12).
           05  MEMBER-ID           PIC 9(10).
           05  PROVIDER-ID         PIC 9(8).
           05  REQUEST-DATE        PIC 9(8).
           05  APPROVAL-DATE       PIC 9(8).
           05  AUTH-STATUS         PIC X(15).
           05  PROCEDURE-CODE      PIC X(5).
           05  DIAGNOSIS-CODE      PIC X(7).
           05  AUTH-AMOUNT         PIC 9(7)V99 COMP-3.
           05  REVIEWER-ID         PIC X(8).
       
       WORKING-STORAGE SECTION.
       01  WS-COUNTERS.
           05  WS-TOTAL-REQUESTS   PIC 9(9) VALUE ZERO.
           05  WS-APPROVED-COUNT   PIC 9(9) VALUE ZERO.
           05  WS-DENIED-COUNT     PIC 9(9) VALUE ZERO.
           05  WS-PENDING-COUNT    PIC 9(9) VALUE ZERO.
           05  WS-FAST-COUNT       PIC 9(9) VALUE ZERO.
           05  WS-STANDARD-COUNT   PIC 9(9) VALUE ZERO.
           05  WS-SLOW-COUNT       PIC 9(9) VALUE ZERO.
           05  WS-OVERDUE-COUNT    PIC 9(9) VALUE ZERO.
       
       01  WS-TURNAROUND-DATA.
           05  WS-TURNAROUND-DAYS  PIC 9(3).
           05  WS-TOTAL-DAYS       PIC 9(9) VALUE ZERO.
           05  WS-AVG-TURNAROUND   PIC 9(3)V99.
           05  WS-MIN-TURNAROUND   PIC 9(3) VALUE 999.
           05  WS-MAX-TURNAROUND   PIC 9(3) VALUE ZERO.
       
       01  WS-TURNAROUND-CATEGORY  PIC X(15).
       
       01  WS-DATE-CALCS.
           05  WS-REQUEST-DATE-NUM PIC 9(8).
           05  WS-APPROVAL-DATE-NUM PIC 9(8).
           05  WS-CURRENT-DATE-NUM PIC 9(8).
       
       01  WS-PERCENTAGES.
           05  WS-APPROVAL-RATE    PIC 9(3)V99.
           05  WS-DENIAL-RATE      PIC 9(3)V99.
           05  WS-FAST-PCT         PIC 9(3)V99.
           05  WS-SLA-COMPLIANCE   PIC 9(3)V99.
       
       01  WS-SLA-THRESHOLD        PIC 9(2) VALUE 7.
       
       01  WS-FLAGS.
           05  EOF-FLAG            PIC X VALUE 'N'.
               88  END-OF-FILE     VALUE 'Y'.
       
       01  WS-ANALYSIS-PERIOD      PIC X(20) VALUE '2023 Q3-Q4'.
       
       PROCEDURE DIVISION.
       MAIN-LOGIC.
           PERFORM OPEN-FILES
           PERFORM PROCESS-PRIOR-AUTHS
           PERFORM CALCULATE-STATISTICS
           PERFORM WRITE-TURNAROUND-REPORT
           PERFORM CLOSE-FILES
           STOP RUN.
       
       OPEN-FILES.
      *    Open prior authorization file from mainframe
      *    Source: PAYER-DEV.ANALYTICS-GOLD.PRIOR-AUTH-SUMMARY
           OPEN INPUT PRIOR-AUTH-FILE
           READ PRIOR-AUTH-FILE
               AT END SET END-OF-FILE TO TRUE
           END-READ.
       
       PROCESS-PRIOR-AUTHS.
      *    Process all prior authorization requests
           ACCEPT WS-CURRENT-DATE-NUM FROM DATE.
           
           PERFORM UNTIL END-OF-FILE
               ADD 1 TO WS-TOTAL-REQUESTS
               
               PERFORM CATEGORIZE-AUTH-STATUS
               PERFORM CALCULATE-TURNAROUND-TIME
               PERFORM CLASSIFY-TURNAROUND
               
               READ PRIOR-AUTH-FILE
                   AT END SET END-OF-FILE TO TRUE
               END-READ
           END-PERFORM.
       
       CATEGORIZE-AUTH-STATUS.
      *    Categorize by authorization status
           EVALUATE AUTH-STATUS
               WHEN 'APPROVED'
                   ADD 1 TO WS-APPROVED-COUNT
               WHEN 'DENIED'
                   ADD 1 TO WS-DENIED-COUNT
               WHEN 'PENDING'
                   ADD 1 TO WS-PENDING-COUNT
               WHEN 'WITHDRAWN'
                   SUBTRACT 1 FROM WS-TOTAL-REQUESTS
           END-EVALUATE.
       
       CALCULATE-TURNAROUND-TIME.
      *    Calculate turnaround time in days
           MOVE REQUEST-DATE TO WS-REQUEST-DATE-NUM.
           
           IF APPROVAL-DATE NOT = ZERO
               MOVE APPROVAL-DATE TO WS-APPROVAL-DATE-NUM
               COMPUTE WS-TURNAROUND-DAYS = 
                   WS-APPROVAL-DATE-NUM - WS-REQUEST-DATE-NUM
           ELSE
      *        Still pending - use current date
               COMPUTE WS-TURNAROUND-DAYS = 
                   WS-CURRENT-DATE-NUM - WS-REQUEST-DATE-NUM
           END-IF.
           
      *    Update statistics
           ADD WS-TURNAROUND-DAYS TO WS-TOTAL-DAYS.
           
           IF WS-TURNAROUND-DAYS < WS-MIN-TURNAROUND
               MOVE WS-TURNAROUND-DAYS TO WS-MIN-TURNAROUND
           END-IF.
           
           IF WS-TURNAROUND-DAYS > WS-MAX-TURNAROUND
               MOVE WS-TURNAROUND-DAYS TO WS-MAX-TURNAROUND
           END-IF.
       
       CLASSIFY-TURNAROUND.
      *    Classify turnaround time category
           EVALUATE TRUE
               WHEN WS-TURNAROUND-DAYS <= 3
                   MOVE 'FAST' TO WS-TURNAROUND-CATEGORY
                   ADD 1 TO WS-FAST-COUNT
               WHEN WS-TURNAROUND-DAYS <= 7
                   MOVE 'STANDARD' TO WS-TURNAROUND-CATEGORY
                   ADD 1 TO WS-STANDARD-COUNT
               WHEN WS-TURNAROUND-DAYS <= 14
                   MOVE 'SLOW' TO WS-TURNAROUND-CATEGORY
                   ADD 1 TO WS-SLOW-COUNT
               WHEN OTHER
                   MOVE 'OVERDUE' TO WS-TURNAROUND-CATEGORY
                   ADD 1 TO WS-OVERDUE-COUNT
           END-EVALUATE.
       
       CALCULATE-STATISTICS.
      *    Calculate summary statistics
           IF WS-TOTAL-REQUESTS > 0
               COMPUTE WS-AVG-TURNAROUND = 
                   WS-TOTAL-DAYS / WS-TOTAL-REQUESTS
               COMPUTE WS-APPROVAL-RATE = 
                   (WS-APPROVED-COUNT / WS-TOTAL-REQUESTS) * 100
               COMPUTE WS-DENIAL-RATE = 
                   (WS-DENIED-COUNT / WS-TOTAL-REQUESTS) * 100
               COMPUTE WS-FAST-PCT = 
                   (WS-FAST-COUNT / WS-TOTAL-REQUESTS) * 100
               COMPUTE WS-SLA-COMPLIANCE = 
                   ((WS-FAST-COUNT + WS-STANDARD-COUNT) / 
                    WS-TOTAL-REQUESTS) * 100
           END-IF.
       
       WRITE-TURNAROUND-REPORT.
      *    Write turnaround analysis report
      *    Target: PAYER-ANALYST.PRIOR-AUTH-REPORTS.TURNAROUND
           DISPLAY '=========================================='
           DISPLAY 'PRIOR AUTHORIZATION TURNAROUND ANALYSIS'
           DISPLAY 'ANALYSIS PERIOD: ' WS-ANALYSIS-PERIOD
           DISPLAY '=========================================='
           DISPLAY ' '
           DISPLAY 'REQUEST VOLUME:'
           DISPLAY '  Total Requests: ' WS-TOTAL-REQUESTS
           DISPLAY '  Approved: ' WS-APPROVED-COUNT
           DISPLAY '  Denied: ' WS-DENIED-COUNT
           DISPLAY '  Pending: ' WS-PENDING-COUNT
           DISPLAY ' '
           DISPLAY 'TURNAROUND TIME DISTRIBUTION:'
           DISPLAY '  Fast (0-3 days): ' WS-FAST-COUNT
           DISPLAY '  Standard (4-7 days): ' WS-STANDARD-COUNT
           DISPLAY '  Slow (8-14 days): ' WS-SLOW-COUNT
           DISPLAY '  Overdue (>14 days): ' WS-OVERDUE-COUNT
           DISPLAY ' '
           DISPLAY 'TURNAROUND STATISTICS:'
           DISPLAY '  Average Turnaround: ' WS-AVG-TURNAROUND ' days'
           DISPLAY '  Minimum: ' WS-MIN-TURNAROUND ' days'
           DISPLAY '  Maximum: ' WS-MAX-TURNAROUND ' days'
           DISPLAY ' '
           DISPLAY 'KEY METRICS:'
           DISPLAY '  Approval Rate: ' WS-APPROVAL-RATE '%'
           DISPLAY '  Denial Rate: ' WS-DENIAL-RATE '%'
           DISPLAY '  Fast Turnaround %: ' WS-FAST-PCT '%'
           DISPLAY '  SLA Compliance (<='WS-SLA-THRESHOLD' days): '
                   WS-SLA-COMPLIANCE '%'
           DISPLAY '=========================================='
           DISPLAY 'ANALYSIS COMPLETE'.
       
       CLOSE-FILES.
           CLOSE PRIOR-AUTH-FILE.


