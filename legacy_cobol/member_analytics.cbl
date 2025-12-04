       IDENTIFICATION DIVISION.
       PROGRAM-ID. MEMBER-CHURN-ANALYSIS.
       AUTHOR. RETENTION-TEAM.
       DATE-WRITTEN. 10/05/2023.
       
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT MEMBER-FILE
               ASSIGN TO "MEMBERS.DAT"
               ORGANIZATION IS LINE SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL.
       
       DATA DIVISION.
       FILE SECTION.
       FD  MEMBER-FILE.
       01  MEMBER-RECORD.
           05  MEMBER-ID           PIC 9(10).
           05  FIRST-NAME          PIC X(20).
           05  LAST-NAME           PIC X(30).
           05  DATE-OF-BIRTH       PIC 9(8).
           05  GENDER              PIC X(1).
           05  AGE                 PIC 9(3).
           05  ENROLLMENT-DATE     PIC 9(8).
           05  TERMINATION-DATE    PIC 9(8).
           05  ENROLLMENT-STATUS   PIC X(10).
           05  PLAN-TYPE           PIC X(20).
           05  PREMIUM-AMOUNT      PIC 9(7)V99 COMP-3.
           05  CLAIMS-LAST-YEAR    PIC 9(5).
           05  TOTAL-COST-LAST-YR  PIC 9(9)V99 COMP-3.
       
       WORKING-STORAGE SECTION.
       01  WS-COUNTERS.
           05  WS-TOTAL-MEMBERS    PIC 9(9) VALUE ZERO.
           05  WS-ACTIVE-MEMBERS   PIC 9(9) VALUE ZERO.
           05  WS-TERMED-MEMBERS   PIC 9(9) VALUE ZERO.
           05  WS-HIGH-RISK-CHURN  PIC 9(9) VALUE ZERO.
           05  WS-MEDICARE-COUNT   PIC 9(9) VALUE ZERO.
           05  WS-COMMERCIAL-COUNT PIC 9(9) VALUE ZERO.
       
       01  WS-RISK-FACTORS.
           05  WS-HIGH-PREMIUM-LIMIT   PIC 9(7)V99 VALUE 500.00.
           05  WS-LOW-UTILIZATION      PIC 9(5) VALUE 2.
           05  WS-HIGH-COST-LIMIT      PIC 9(9)V99 VALUE 50000.00.
       
       01  WS-ANALYTICS.
           05  WS-AVG-PREMIUM      PIC 9(7)V99.
           05  WS-AVG-CLAIMS       PIC 9(5)V99.
           05  WS-AVG-COST         PIC 9(9)V99.
           05  WS-CHURN-RATE       PIC 9(3)V99.
           05  WS-RETENTION-RATE   PIC 9(3)V99.
       
       01  WS-CHURN-SCORE          PIC 9(3) VALUE ZERO.
       01  WS-RISK-CATEGORY        PIC X(15).
       
       01  WS-FLAGS.
           05  EOF-FLAG            PIC X VALUE 'N'.
               88  END-OF-FILE     VALUE 'Y'.
       
       01  WS-ANALYSIS-PERIOD      PIC X(20) VALUE '2023 FULL YEAR'.
       
       PROCEDURE DIVISION.
       MAIN-LOGIC.
           PERFORM OPEN-FILES
           PERFORM PROCESS-MEMBERS
           PERFORM CALCULATE-ANALYTICS
           PERFORM WRITE-CHURN-REPORT
           PERFORM CLOSE-FILES
           STOP RUN.
       
       OPEN-FILES.
      *    Open member file from mainframe
      *    Source: PAYER-DEV.ANALYTICS-GOLD.MEMBERS
           OPEN INPUT MEMBER-FILE
           READ MEMBER-FILE
               AT END SET END-OF-FILE TO TRUE
           END-READ.
       
       PROCESS-MEMBERS.
      *    Process all members and analyze churn risk
           PERFORM UNTIL END-OF-FILE
               ADD 1 TO WS-TOTAL-MEMBERS
               
               PERFORM CATEGORIZE-MEMBER-STATUS
               PERFORM CLASSIFY-PLAN-TYPE
               PERFORM ASSESS-CHURN-RISK
               
               READ MEMBER-FILE
                   AT END SET END-OF-FILE TO TRUE
               END-READ
           END-PERFORM.
       
       CATEGORIZE-MEMBER-STATUS.
      *    Categorize by enrollment status
           EVALUATE ENROLLMENT-STATUS
               WHEN 'ACTIVE'
                   ADD 1 TO WS-ACTIVE-MEMBERS
               WHEN 'TERMINATED'
                   ADD 1 TO WS-TERMED-MEMBERS
               WHEN 'SUSPENDED'
                   ADD 1 TO WS-TERMED-MEMBERS
           END-EVALUATE.
       
       CLASSIFY-PLAN-TYPE.
      *    Classify by plan type
           EVALUATE TRUE
               WHEN PLAN-TYPE = 'MEDICARE' OR
                    PLAN-TYPE = 'MEDICARE-ADVANTAGE'
                   ADD 1 TO WS-MEDICARE-COUNT
               WHEN PLAN-TYPE = 'COMMERCIAL' OR
                    PLAN-TYPE = 'INDIVIDUAL' OR
                    PLAN-TYPE = 'GROUP'
                   ADD 1 TO WS-COMMERCIAL-COUNT
           END-EVALUATE.
       
       ASSESS-CHURN-RISK.
      *    Assess member churn risk
           MOVE ZERO TO WS-CHURN-SCORE
           
      *    High premium increases churn risk
           IF PREMIUM-AMOUNT > WS-HIGH-PREMIUM-LIMIT
               ADD 30 TO WS-CHURN-SCORE
           END-IF
           
      *    Low utilization increases churn risk
           IF CLAIMS-LAST-YEAR < WS-LOW-UTILIZATION
               ADD 25 TO WS-CHURN-SCORE
           END-IF
           
      *    High cost might indicate satisfaction/need
           IF TOTAL-COST-LAST-YR > WS-HIGH-COST-LIMIT
               SUBTRACT 20 FROM WS-CHURN-SCORE
           END-IF
           
      *    Age factor (younger = higher churn)
           IF AGE < 30
               ADD 20 TO WS-CHURN-SCORE
           END-IF
           
           PERFORM CLASSIFY-CHURN-RISK.
       
       CLASSIFY-CHURN-RISK.
      *    Classify churn risk category
           EVALUATE TRUE
               WHEN WS-CHURN-SCORE >= 70
                   MOVE 'CRITICAL' TO WS-RISK-CATEGORY
                   ADD 1 TO WS-HIGH-RISK-CHURN
               WHEN WS-CHURN-SCORE >= 50
                   MOVE 'HIGH' TO WS-RISK-CATEGORY
                   ADD 1 TO WS-HIGH-RISK-CHURN
               WHEN WS-CHURN-SCORE >= 30
                   MOVE 'MEDIUM' TO WS-RISK-CATEGORY
               WHEN OTHER
                   MOVE 'LOW' TO WS-RISK-CATEGORY
           END-EVALUATE.
       
       CALCULATE-ANALYTICS.
      *    Calculate summary analytics
           IF WS-TOTAL-MEMBERS > 0
               COMPUTE WS-CHURN-RATE = 
                   (WS-TERMED-MEMBERS / WS-TOTAL-MEMBERS) * 100
               COMPUTE WS-RETENTION-RATE = 
                   (WS-ACTIVE-MEMBERS / WS-TOTAL-MEMBERS) * 100
           END-IF.
       
       WRITE-CHURN-REPORT.
      *    Write output to: PAYER-ANALYST.MEMBER-ANALYTICS.CHURN-ANALYSIS
           DISPLAY '=========================================='
           DISPLAY 'MEMBER CHURN ANALYSIS REPORT'
           DISPLAY 'ANALYSIS PERIOD: ' WS-ANALYSIS-PERIOD
           DISPLAY '=========================================='
           DISPLAY ' '
           DISPLAY 'MEMBER STATISTICS:'
           DISPLAY '  Total Members: ' WS-TOTAL-MEMBERS
           DISPLAY '  Active: ' WS-ACTIVE-MEMBERS
           DISPLAY '  Terminated: ' WS-TERMED-MEMBERS
           DISPLAY '  High Churn Risk: ' WS-HIGH-RISK-CHURN
           DISPLAY ' '
           DISPLAY 'PLAN TYPE DISTRIBUTION:'
           DISPLAY '  Medicare/MA: ' WS-MEDICARE-COUNT
           DISPLAY '  Commercial: ' WS-COMMERCIAL-COUNT
           DISPLAY ' '
           DISPLAY 'KEY METRICS:'
           DISPLAY '  Churn Rate: ' WS-CHURN-RATE '%'
           DISPLAY '  Retention Rate: ' WS-RETENTION-RATE '%'
           DISPLAY ' '
           DISPLAY 'CHURN RISK FACTORS:'
           DISPLAY '  High Premium Threshold: $' 
                   WS-HIGH-PREMIUM-LIMIT
           DISPLAY '  Low Utilization Threshold: ' 
                   WS-LOW-UTILIZATION ' claims/year'
           DISPLAY '  High Cost Threshold: $' 
                   WS-HIGH-COST-LIMIT
           DISPLAY '=========================================='
           DISPLAY 'ANALYSIS COMPLETE'.
       
       CLOSE-FILES.
           CLOSE MEMBER-FILE.


