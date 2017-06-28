init:
	mkdir logs
	mkdir ~/tgbackup
	mkdir ~/tgbackup/logs

clean:
	rm logs/*

backup:
	cp dump.rdb ~/tgbackup
	cp -R logs ~/tgbackup
