       IDENTIFICATION DIVISION.
       PROGRAM-ID. RAF-SCORE-CALC.
       AUTHOR. RISK-ADJUSTMENT-TEAM.
       DATE-WRITTEN. 08/10/2023.
       
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT MEMBER-FILE
               ASSIGN TO "MEMBERS.DAT"
               ORGANIZATION IS LINE SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL.
           SELECT DIAGNOSIS-FILE
               ASSIGN TO "DIAGNOSES.DAT"
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
           05  AGE                 PIC 9(3).
           05  GENDER              PIC X(1).
           05  DISABLED-FLAG       PIC X(1).
           05  ORIGINAL-ENTITLED   PIC X(1).
       
       FD  DIAGNOSIS-FILE.
       01  DIAGNOSIS-RECORD.
           05  MEMBER-ID           PIC 9(10).
           05  DIAGNOSIS-CODE      PIC X(7).
           05  HCC-CODE            PIC X(6).
           05  SERVICE-DATE        PIC 9(8).
           05  HCC-WEIGHT          PIC 9V9999 COMP-3.
       
       WORKING-STORAGE SECTION.
       01  WS-RAF-COMPONENTS.
           05  BASE-RAF-SCORE      PIC 9V9999 VALUE 1.0000.
           05  AGE-SEX-FACTOR      PIC 9V9999 VALUE ZERO.
           05  HCC-FACTOR          PIC 9V9999 VALUE ZERO.
           05  DISABLED-FACTOR     PIC 9V9999 VALUE ZERO.
           05  TOTAL-RAF-SCORE     PIC 9V9999 VALUE ZERO.
       
       01  WS-HCC-WEIGHTS.
      *    Common HCC weights (CMS-HCC Model V24)
           05  HCC-17-WEIGHT       PIC 9V9999 VALUE 0.3180.
           05  HCC-18-WEIGHT       PIC 9V9999 VALUE 0.3180.
           05  HCC-19-WEIGHT       PIC 9V9999 VALUE 0.3180.
           05  HCC-85-WEIGHT       PIC 9V9999 VALUE 0.4190.
           05  HCC-111-WEIGHT      PIC 9V9999 VALUE 0.3280.
           05  HCC-112-WEIGHT      PIC 9V9999 VALUE 0.3280.
       
       01  WS-HCC-FLAGS.
           05  DIABETES-FLAG       PIC X VALUE 'N'.
               88  HAS-DIABETES    VALUE 'Y'.
           05  CHF-FLAG            PIC X VALUE 'N'.
               88  HAS-CHF         VALUE 'Y'.
           05  COPD-FLAG           PIC X VALUE 'N'.
               88  HAS-COPD        VALUE 'Y'.
       
       01  WS-COUNTERS.
           05  WS-MEMBERS-SCORED   PIC 9(9) VALUE ZERO.
           05  WS-HIGH-RAF-COUNT   PIC 9(9) VALUE ZERO.
       
       01  WS-FLAGS.
           05  EOF-MEMBER          PIC X VALUE 'N'.
               88  END-OF-MEMBERS  VALUE 'Y'.
           05  EOF-DIAGNOSIS       PIC X VALUE 'N'.
               88  END-OF-DIAG     VALUE 'Y'.
       
       01  WS-MODEL-YEAR           PIC 9(4) VALUE 2023.
       01  WS-CURRENT-MEMBER       PIC 9(10).
       
       PROCEDURE DIVISION.
       MAIN-LOGIC.
           PERFORM OPEN-FILES
           PERFORM PROCESS-ALL-MEMBERS
           PERFORM WRITE-RAF-REPORT
           PERFORM CLOSE-FILES
           STOP RUN.
       
       OPEN-FILES.
      *    Open input files from mainframe
      *    Source: PAYER-DEV.ANALYTICS-GOLD.MEMBERS
      *    Source: PAYER-DEV.ANALYTICS-GOLD.DIAGNOSES
           OPEN INPUT MEMBER-FILE
           OPEN INPUT DIAGNOSIS-FILE
           READ MEMBER-FILE
               AT END SET END-OF-MEMBERS TO TRUE
           END-READ
           READ DIAGNOSIS-FILE
               AT END SET END-OF-DIAG TO TRUE
           END-READ.
       
       PROCESS-ALL-MEMBERS.
      *    Calculate RAF score for each member
           PERFORM UNTIL END-OF-MEMBERS
               MOVE MEMBER-ID TO WS-CURRENT-MEMBER
               PERFORM INITIALIZE-RAF-CALC
               PERFORM CALCULATE-AGE-SEX-FACTOR
               PERFORM CALCULATE-DISABLED-FACTOR
               PERFORM PROCESS-HCC-CONDITIONS
               PERFORM COMPUTE-TOTAL-RAF
               PERFORM WRITE-MEMBER-RAF
               
               READ MEMBER-FILE
                   AT END SET END-OF-MEMBERS TO TRUE
               END-READ
           END-PERFORM.
       
       INITIALIZE-RAF-CALC.
      *    Initialize RAF calculation for member
           MOVE 1.0000 TO BASE-RAF-SCORE
           MOVE ZERO TO AGE-SEX-FACTOR
           MOVE ZERO TO HCC-FACTOR
           MOVE ZERO TO DISABLED-FACTOR
           MOVE 'N' TO DIABETES-FLAG
           MOVE 'N' TO CHF-FLAG
           MOVE 'N' TO COPD-FLAG.
       
       CALCULATE-AGE-SEX-FACTOR.
      *    Calculate age-sex demographic factor
           IF GENDER = 'M'
               EVALUATE TRUE
                   WHEN AGE >= 85
                       MOVE 1.5000 TO AGE-SEX-FACTOR
                   WHEN AGE >= 75
                       MOVE 1.3000 TO AGE-SEX-FACTOR
                   WHEN AGE >= 65
                       MOVE 1.1000 TO AGE-SEX-FACTOR
                   WHEN AGE >= 55
                       MOVE 0.9000 TO AGE-SEX-FACTOR
                   WHEN OTHER
                       MOVE 0.8000 TO AGE-SEX-FACTOR
               END-EVALUATE
           ELSE
               EVALUATE TRUE
                   WHEN AGE >= 85
                       MOVE 1.4500 TO AGE-SEX-FACTOR
                   WHEN AGE >= 75
                       MOVE 1.2500 TO AGE-SEX-FACTOR
                   WHEN AGE >= 65
                       MOVE 1.0500 TO AGE-SEX-FACTOR
                   WHEN AGE >= 55
                       MOVE 0.8500 TO AGE-SEX-FACTOR
                   WHEN OTHER
                       MOVE 0.7500 TO AGE-SEX-FACTOR
               END-EVALUATE
           END-IF.
       
       CALCULATE-DISABLED-FACTOR.
      *    Add disabled beneficiary factor if applicable
           IF DISABLED-FLAG = 'Y'
               IF ORIGINAL-ENTITLED = 'Y'
                   MOVE 0.5000 TO DISABLED-FACTOR
               ELSE
                   MOVE 0.3000 TO DISABLED-FACTOR
               END-IF
           END-IF.
       
       PROCESS-HCC-CONDITIONS.
      *    Process HCC conditions for member
           PERFORM UNTIL END-OF-DIAG OR 
                        MEMBER-ID NOT = WS-CURRENT-MEMBER
               PERFORM CHECK-HCC-CATEGORY
               READ DIAGNOSIS-FILE
                   AT END SET END-OF-DIAG TO TRUE
               END-READ
           END-PERFORM.
       
       CHECK-HCC-CATEGORY.
      *    Identify and weight HCC categories
           EVALUATE HCC-CODE
               WHEN 'HCC17'
               WHEN 'HCC18'
               WHEN 'HCC19'
                   SET HAS-DIABETES TO TRUE
                   ADD HCC-17-WEIGHT TO HCC-FACTOR
               WHEN 'HCC85'
                   SET HAS-CHF TO TRUE
                   ADD HCC-85-WEIGHT TO HCC-FACTOR
               WHEN 'HCC111'
               WHEN 'HCC112'
                   SET HAS-COPD TO TRUE
                   ADD HCC-111-WEIGHT TO HCC-FACTOR
           END-EVALUATE.
       
       COMPUTE-TOTAL-RAF.
      *    Compute total RAF score
           COMPUTE TOTAL-RAF-SCORE = BASE-RAF-SCORE + 
                                     AGE-SEX-FACTOR + 
                                     HCC-FACTOR + 
                                     DISABLED-FACTOR.
           
           ADD 1 TO WS-MEMBERS-SCORED.
           
      *    Flag high RAF scores for review
           IF TOTAL-RAF-SCORE > 3.0000
               ADD 1 TO WS-HIGH-RAF-COUNT
           END-IF.
       
       WRITE-MEMBER-RAF.
      *    Write RAF score to output table
      *    Target: PAYER-ANALYST.RISK-ADJUSTMENT.MEMBER-RAF-SCORES
           DISPLAY 'MEMBER ' WS-CURRENT-MEMBER 
                   ' RAF SCORE: ' TOTAL-RAF-SCORE.
       
       WRITE-RAF-REPORT.
      *    Write summary report
           DISPLAY '=========================================='
           DISPLAY 'RAF SCORE CALCULATION REPORT'
           DISPLAY 'MODEL YEAR: ' WS-MODEL-YEAR
           DISPLAY '=========================================='
           DISPLAY ' '
           DISPLAY 'MEMBERS SCORED: ' WS-MEMBERS-SCORED
           DISPLAY 'HIGH RAF (>3.0): ' WS-HIGH-RAF-COUNT
           DISPLAY ' '
           DISPLAY 'HCC WEIGHTS APPLIED:'
           DISPLAY '  HCC 17-19 (Diabetes): ' HCC-17-WEIGHT
           DISPLAY '  HCC 85 (CHF): ' HCC-85-WEIGHT
           DISPLAY '  HCC 111-112 (COPD): ' HCC-111-WEIGHT
           DISPLAY '=========================================='
           DISPLAY 'RAF CALCULATION COMPLETE'.
       
       CLOSE-FILES.
           CLOSE MEMBER-FILE
           CLOSE DIAGNOSIS-FILE.


