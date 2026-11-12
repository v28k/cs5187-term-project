# Beamer decks: slides and speaker-notes PDFs
all: final_presentation.pdf final_presentation_notes.pdf class_talk.pdf class_talk_notes.pdf
%.pdf: %.tex common.tex arch_main.tex arch_gen.tex
	pdflatex -interaction=nonstopmode $< && pdflatex -interaction=nonstopmode $<
%_notes.pdf: %.tex common.tex arch_main.tex arch_gen.tex
	pdflatex -interaction=nonstopmode -jobname=$*_notes '\def\shownotes{1}\input{$*}'
	pdflatex -interaction=nonstopmode -jobname=$*_notes '\def\shownotes{1}\input{$*}'
clean:
	rm -f *.aux *.log *.nav *.out *.snm *.toc *.vrb
.PHONY: all clean
