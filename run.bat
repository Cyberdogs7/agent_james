@echo off
echo Starting Ada-V2...
call conda activate ada_v2
npm run dev %*
