# dspace-stats-db 

Supplemental scripting to import dspace 7 api usage stats into a postgresql instnace. Using foreign data wrapper (fdw), these tables can be imported as foreign tables in dspace database allowing easier reporting for file view and downloads with all relevant metadata and grouping by collections/communities. 

Each script runs as a cronjob and data is updated or inserted depending existance of uuid. 
