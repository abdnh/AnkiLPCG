.PHONY: all docs zip ankiweb clean

all: zip ankiweb
docs:
	$(MAKE) -C docs html
zip:
	python -m ankibuild --type package --install --qt all
ankiweb:
	python -m ankibuild --type ankiweb --install --qt all
run:
	python -m ankirun
clean:
	make -C docs clean
	rm -rf build/
