Example files showing what voc4cat can do:

- `Photocatalysis_LIKAT_template043_orig-fixed.xlsx`
  - A draft of a photocatalysis vocabulary: This has still the original structure and contents; only spelling and link errors were fixed.
  - The hierarchy was created with voc4cat 0.30 by the `-r` / `--add-related` option from the extra column on the right in sheets Concepts & Collections. Note, this option was removed in 0.4.0 to foster using numeric IDs.
- `Photocatalysis_LIKAT_template043_textids.xlsx`
  - Same contents as the first file but the extra column in the sheets Concepts & Collections was removed. The concepts were sorted by IRI (this was done to assign IDs in a reproducible way to domonstrate round-tripping, see below).
- `Photocatalysis_LIKAT_template043_final.xlsx`
  - This file was generate from the previous one by replacing the textual IDs with numeric ones using the `--make-ids` option added in version 0.4.0.
- `Photocatalysis_LIKAT_template043_final.ttl`
  - Results of processing the previous file with voc4cat without options (which does convert to turtle).

The above example may not represent the most typical workflow.
In practice one would start creating vocabularies from a file that does not yet have IRIs.
In this case hierarchies may be expressed by indentation:

- `Photocatalysis_LIKAT_template043_indent.xlsx`
  - Same content as first file, but it uses Excel indentation to express hierarchy. It does contain temporary IRIs for concepts created from the preferred label with Excel functions.
- `Photocatalysis_LIKAT_template043_from-indent.xlsx`
  - This results from processing the previous file with voc4cat using the `--hierarchy-from-indent` option. The concepts were sorted by IRI (like above).
- `Photocatalysis_LIKAT_template043_from-indent_final.xlsx`
  - This results from processing the previous file with voc4cat using the `--make-ids new 1001` option which replaces the temporary IRIs with IRIs containing  numeric IDs.
  - If this file is further processed with voc4cat without options, a turtle file is generated that is identical to the turtle file from above. - So round-tripping does work!

Files demonstrating the different ways how to express concept-hierarchies:

- Children URIs: `concept_hierarchy_043_4Cat.xlsx`
- Excel indentation: `indent_043_4Cat.xlsx`
- Three spaces for indentation: `indent_3spaces_043_4Cat.xlsx`
