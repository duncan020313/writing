LATEX = pdflatex
LATEXFLAGS = -interaction=nonstopmode -shell-escape


TEX_FILES := $(shell find . -type f -name "*.tex")
PDF_FILES := $(TEX_FILES:.tex=.pdf)


all: $(PDF_FILES)


%.pdf: %.tex
	@cd $(dir $<) && $(LATEX) $(LATEXFLAGS) $(notdir $<)
	@cd $(dir $<) && $(LATEX) $(LATEXFLAGS) $(notdir $<)  


clean:
	@find . -type f \( \
		-name "*.aux" -o \
		-name "*.log" -o \
		-name "*.out" -o \
		-name "*.toc" -o \
		-name "*.bbl" -o \
		-name "*.blg" -o \
		-name "*.synctex.gz" \
	\) -delete


cleanall: clean
	@find . -type f -name "*.pdf" -delete

.PHONY: all clean cleanall
