       IDENTIFICATION DIVISION.
       PROGRAM-ID. HEDIS-BCS-SUMMARY.
       AUTHOR. PAYER-ANALYTICS-TEAM.
       DATE-WRITTEN. 11/15/2023.
       
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT MEMBER-FILE
               ASSIGN TO "MEMBERS.DAT"
               ORGANIZATION IS LINE SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL.
           SELECT CLAIM-FILE
               ASSIGN TO "CLAIMS.DAT"
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
           05  ENROLLMENT-STATUS   PIC X(10).
           05  ENROLLMENT-MONTHS   PIC 9(2).
       
       FD  CLAIM-FILE.
       01  CLAIM-RECORD.
           05  CLAIM-ID            PIC 9(12).
           05  MEMBER-ID           PIC 9(10).
           05  SERVICE-DATE        PIC 9(8).
           05  PROCEDURE-CODE      PIC X(5).
           05  DIAGNOSIS-CODE      PIC X(7).
           05  CLAIM-AMOUNT        PIC 9(7)V99 COMP-3.
       
       WORKING-STORAGE SECTION.
       01  WS-COUNTERS.
           05  WS-DENOMINATOR      PIC 9(7) VALUE ZERO.
           05  WS-NUMERATOR        PIC 9(7) VALUE ZERO.
           05  WS-AGE-50-59        PIC 9(7) VALUE ZERO.
           05  WS-AGE-60-69        PIC 9(7) VALUE ZERO.
           05  WS-AGE-70-74        PIC 9(7) VALUE ZERO.
       
       01  WS-MEASURE-YEAR         PIC 9(4) VALUE 2023.
       01  WS-COMPLIANCE-RATE      PIC 9(3)V99.
       01  WS-AGE-GROUP            PIC X(10).
       
       01  WS-MAMMOGRAM-CODES.
           05  WS-MAMMO-CODE       OCCURS 3 TIMES PIC X(5).
       
       01  WS-FLAGS.
           05  EOF-MEMBER          PIC X VALUE 'N'.
               88  END-OF-MEMBERS  VALUE 'Y'.
           05  EOF-CLAIM           PIC X VALUE 'N'.
               88  END-OF-CLAIMS   VALUE 'Y'.
       
       PROCEDURE DIVISION.
       MAIN-LOGIC.
           PERFORM INITIALIZE-PROGRAM
           PERFORM READ-MEMBERS
           PERFORM CALC-DENOMINATOR
           PERFORM READ-CLAIMS
           PERFORM CALC-NUMERATOR
           PERFORM CALC-RATES
           PERFORM WRITE-REPORT
           STOP RUN.
       
       INITIALIZE-PROGRAM.
      *    Initialize mammogram procedure codes
           MOVE '77065' TO WS-MAMMO-CODE(1)
           MOVE '77066' TO WS-MAMMO-CODE(2)
           MOVE '77067' TO WS-MAMMO-CODE(3).
       
       READ-MEMBERS.
      *    Open member file
           OPEN INPUT MEMBER-FILE
           READ MEMBER-FILE
               AT END SET END-OF-MEMBERS TO TRUE
           END-READ.
       
       CALC-DENOMINATOR.
      *    Calculate BCS denominator: Women ages 50-74
      *    From mainframe table: PAYER-DEV.ANALYTICS-GOLD.MEMBERS
           PERFORM UNTIL END-OF-MEMBERS
               IF GENDER = 'F'
                   IF AGE >= 50 AND AGE <= 74
                       IF ENROLLMENT-STATUS = 'ACTIVE'
                           IF ENROLLMENT-MONTHS = 12
                               ADD 1 TO WS-DENOMINATOR
                               PERFORM CLASSIFY-AGE-GROUP
                           END-IF
                       END-IF
                   END-IF
               END-IF
               READ MEMBER-FILE
                   AT END SET END-OF-MEMBERS TO TRUE
               END-READ
           END-PERFORM
           CLOSE MEMBER-FILE.
       
       CLASSIFY-AGE-GROUP.
      *    Classify member into age groups
           EVALUATE TRUE
               WHEN AGE >= 50 AND AGE <= 59
                   ADD 1 TO WS-AGE-50-59
                   MOVE '50-59' TO WS-AGE-GROUP
               WHEN AGE >= 60 AND AGE <= 69
                   ADD 1 TO WS-AGE-60-69
                   MOVE '60-69' TO WS-AGE-GROUP
               WHEN AGE >= 70 AND AGE <= 74
                   ADD 1 TO WS-AGE-70-74
                   MOVE '70-74' TO WS-AGE-GROUP
           END-EVALUATE.
       
       READ-CLAIMS.
      *    Open claims file
           OPEN INPUT CLAIM-FILE
           READ CLAIM-FILE
               AT END SET END-OF-CLAIMS TO TRUE
           END-READ.
       
       CALC-NUMERATOR.
      *    Calculate BCS numerator: Members with mammogram
      *    From mainframe table: PAYER-DEV.ANALYTICS-GOLD.CLAIMS
           PERFORM UNTIL END-OF-CLAIMS
               PERFORM CHECK-MAMMOGRAM-CODE
               READ CLAIM-FILE
                   AT END SET END-OF-CLAIMS TO TRUE
               END-READ
           END-PERFORM
           CLOSE CLAIM-FILE.
       
       CHECK-MAMMOGRAM-CODE.
      *    Check if claim has mammogram procedure code
           PERFORM VARYING WS-I FROM 1 BY 1 UNTIL WS-I > 3
               IF PROCEDURE-CODE = WS-MAMMO-CODE(WS-I)
                   ADD 1 TO WS-NUMERATOR
               END-IF
           END-PERFORM.
       
       CALC-RATES.
      *    Calculate compliance rates
           IF WS-DENOMINATOR > 0
               COMPUTE WS-COMPLIANCE-RATE = 
                   (WS-NUMERATOR / WS-DENOMINATOR) * 100
           ELSE
               MOVE ZERO TO WS-COMPLIANCE-RATE
           END-IF.
       
       WRITE-REPORT.
      *    Write output to: PAYER-ANALYST.HEDIS-REPORTS.BCS-SUMMARY
           DISPLAY '=========================================='
           DISPLAY 'HEDIS BCS (BREAST CANCER SCREENING) REPORT'
           DISPLAY 'MEASUREMENT YEAR: ' WS-MEASURE-YEAR
           DISPLAY '=========================================='
           DISPLAY ' '
           DISPLAY 'DENOMINATOR (ELIGIBLE WOMEN): ' WS-DENOMINATOR
           DISPLAY 'NUMERATOR (HAD MAMMOGRAM): ' WS-NUMERATOR
           DISPLAY 'COMPLIANCE RATE: ' WS-COMPLIANCE-RATE '%'
           DISPLAY ' '
           DISPLAY 'AGE GROUP BREAKDOWN:'
           DISPLAY '  50-59: ' WS-AGE-50-59
           DISPLAY '  60-69: ' WS-AGE-60-69
           DISPLAY '  70-74: ' WS-AGE-70-74
           DISPLAY '=========================================='
           DISPLAY 'REPORT COMPLETE'.


