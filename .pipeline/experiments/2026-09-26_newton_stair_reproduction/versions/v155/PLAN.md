# v155 separate warm initialization from safety sample density

Stage: experiment + analysis. Native parent v151; host parent v153.
One native correction: carry the original coarse division count separately from
the actual collision-check sample count, and use only that coarse count for
remaining-curve warm initialization. v151retains every original safety sample
and adds four interiors; all of those checks and original rejection/budget gates
remain unchanged. This version removes unintended initializer geometry/timing
changes caused by reading the refined safety count as a seed grid size.

Compare actual native manager warm seeds on the same accepted original-input
curve: parentv147 and v155must return bit-identical seed points/interval when
both admit it. Preserve the v151 coupled control. Recheck the v150 bad curve
rejection, original native tests and actual graph, then freeze before physical
original-start tests. A passed seed regression does not prove recovery.
