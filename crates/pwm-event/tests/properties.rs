use std::collections::BTreeMap;

use proptest::prelude::*;
use pwm_canonical::{EventBodyCid, Value, encode};
use pwm_event::deterministic_topological_order;

fn cid(index: u64) -> EventBodyCid {
    EventBodyCid::from_canonical_bytes(&encode(&Value::Unsigned(index)).unwrap())
}

proptest! {
    #[test]
    fn replay_is_permutation_invariant_and_parent_first(
        node_count in 1usize..200,
        insertion_keys in proptest::collection::vec(any::<u64>(), 1..400),
    ) {
        let mut nodes = (0..node_count)
            .map(|index| {
                let parents = if index == 0 { vec![] } else { vec![cid((index - 1) as u64)] };
                (cid(index as u64), parents)
            })
            .collect::<Vec<_>>();
        nodes.sort_by_key(|(node, _)| {
            let index = u64::from(node.as_bytes()[node.as_bytes().len() - 1]);
            insertion_keys[index as usize % insertion_keys.len()]
        });
        let graph: BTreeMap<_, _> = nodes.clone().into_iter().collect();

        let order = deterministic_topological_order(&graph).unwrap();
        let positions: BTreeMap<_, _> = order
            .iter()
            .enumerate()
            .map(|(position, node)| (*node, position))
            .collect();
        for (child, parents) in &graph {
            for parent in parents {
                prop_assert!(positions[parent] < positions[child]);
            }
        }

        nodes.reverse();
        let reversed: BTreeMap<_, _> = nodes.into_iter().collect();
        prop_assert_eq!(deterministic_topological_order(&reversed).unwrap(), order);
    }
}
