#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit AI
# 2024 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# Splay tree library with root-oriented Search results.
#
# This module implements a top-down splay tree rather than a height-balanced
# tree.  Every lookup, insertion, update, and deletion moves the accessed key
# (or the last key encountered) toward the root.  Frequently used keys therefore
# become cheap to access without storing explicit balance factors or colors.
#
# There are two linked representations of the same set of nodes:
#
# * ``left`` and ``right`` form the binary-search-tree structure used for
#   splaying and persistence.
# * ``previous`` and ``next`` form a sorted doubly linked list used for fast
#   ordered traversal.
#
# Any operation that changes membership must maintain both representations and
# the ``head``, ``tail``, and ``count`` metadata.  ``Validate`` checks these
# invariants after tests or bulk modifications.
#
# All key ordering and equality decisions go through the assignable
# ``tree.CompareKeys`` callable.  The default compares ``str(key)`` values;
# callers can replace it on one tree, for example with
# ``tree.CompareKeys = my_comparator``.  A comparator must accept two keys and
# return a negative, zero, or positive integer.

import sys
import os
import json
import random

def CompareStrings(left, right):
    # Default comparator: convert both keys to strings and compare lexically.
    # This deliberately gives callers one small, predictable policy that can
    # be replaced per tree without changing the tree algorithms.
    left = str(left)
    right = str(right)
    if left < right:
        return -1
    if left > right:
        return 1
    return 0


class SplayNode:
    # One node in the Splay tree.
    #
    # ``key`` is retained exactly as supplied by the caller.  ``value`` is
    # opaque to the tree.  The four links are deliberately kept separate:
    # tree links describe search structure, while list links describe sorted
    # order and do not participate in rotations.
    def __init__(self, key, value=None):
        self.key = key
        self.value = value
        self.left = None
        self.right = None
        self.previous = None
        self.next = None


class SplayTree:
    # A self-adjusting binary Search tree.
    #
    # Expected amortized cost for splay operations is O(log n), although an
    # individual operation can be O(n).  The implementation does not promise
    # a small worst-case height at every instant.
    def __init__(self):
        self.root = None
        self.head = None
        self.tail = None
        self.count = 0
        self.random = random.SystemRandom()
        # Instance attribute is intentional: callers may replace it with any
        # compatible comparator before inserting or searching keys.
        self.CompareKeys = CompareStrings

    def __len__(self):
        # Return the maintained number of unique keys, not a traversal count.
        return self.count

    def IsEmpty(self):
        # The root is the authoritative emptiness check.
        return self.root is None

    def RotateRight(self, node):
        # Promote the left child and make the old root its right child.
        # The caller guarantees that ``node.left`` is not None.
        child = node.left
        node.left = child.right
        child.right = node
        return child

    def RotateLeft(self, node):
        # Promote the right child and make the old root its left child.
        # The caller guarantees that ``node.right`` is not None.
        child = node.right
        node.right = child.left
        child.left = node
        return child

    def Splay(self, root, key):
        # Iterative top-down splaying uses rotations in both directions.
        #
        # ``header`` is a temporary sentinel.  ``leftTree`` collects nodes
        # known to be smaller than the search key and ``rightTree`` collects
        # nodes known to be larger.  The loop performs a zig-zig rotation when
        # two consecutive links point in the search direction; otherwise it
        # links one node into the appropriate temporary tree.  The final four
        # assignments reassemble both temporary trees around the stopping node.
        #
        # The returned root is either the exact match or the closest node at
        # which the search stopped.  That property lets Insert and Delete
        # decide membership without a second traversal.
        if root is None or self.CompareKeys(root.key, key) == 0:
            return root

        header = SplayNode(None)
        leftTree = header
        rightTree = header

        while True:
            comparison = self.CompareKeys(key, root.key)
            if comparison < 0:
                if root.left is None:
                    break
                if self.CompareKeys(key, root.left.key) < 0:
                    root = self.RotateRight(root)
                    if root.left is None:
                        break
                rightTree.left = root
                rightTree = root
                root = root.left
            elif comparison > 0:
                if root.right is None:
                    break
                if self.CompareKeys(key, root.right.key) > 0:
                    root = self.RotateLeft(root)
                    if root.right is None:
                        break
                leftTree.right = root
                leftTree = root
                root = root.right
            else:
                break

        leftTree.right = root.left
        rightTree.left = root.right
        root.left = header.right
        root.right = header.left
        return root

    def Search(self, key, SplayMissing=True):
        # The returned answer is always the root or None.
        # ``SplayMissing`` is retained for API compatibility but is unused.
        # A missing search still changes the tree by splaying the last
        # candidate to the root, which is central to splay-tree performance.
        self.root = self.Splay(self.root, key)
        if self.root is None or self.CompareKeys(self.root.key, key) != 0:
            return None
        return self.root.value

    def Contains(self, key, SplayMissing=True):
        # Check whether the exact key is now the root.
        # As with Search, the compatibility flag is accepted but ignored.
        self.root = self.Splay(self.root, key)
        return self.root is not None and self.CompareKeys(self.root.key, key) == 0

    def Insert(self, key, value=None):
        # Insert only an original key, link it in sorted order, and make it root.
        #
        # Duplicate keys are rejected rather than updated.  On success the
        # new node becomes the root, and its predecessor/successor are found
        # from the two subtrees exposed by the preceding splay.
        if self.root is None:
            self.root = SplayNode(key, value)
            self.head = self.root
            self.tail = self.root
            self.count = 1
            return True

        self.root = self.Splay(self.root, key)

        if self.CompareKeys(self.root.key, key) == 0:
            # The existing value is intentionally preserved on duplicates.
            return False

        node = SplayNode(key, value)
        if self.CompareKeys(key, self.root.key) < 0:
            # The current root is the successor of the new node.
            successor = self.root
            predecessor = self.MaximumNode(self.root.left)
            node.left = self.root.left
            node.right = self.root
            self.root.left = None
        else:
            # The current root is the predecessor of the new node.
            predecessor = self.root
            successor = self.MinimumNode(self.root.right)
            node.right = self.root.right
            node.left = self.root
            self.root.right = None

        node.previous = predecessor
        node.next = successor
        if predecessor is None:
            self.head = node
        else:
            predecessor.next = node
        if successor is None:
            self.tail = node
        else:
            successor.previous = node

        self.root = node
        self.count += 1
        return True

    def JoinAfterDelete(self, left, right):
        # Randomly choose predecessor or successor reconstruction.
        #
        # Both subtrees contain keys on only one side of the deleted key.  If
        # both exist, splaying an extreme key makes that node a root with an
        # empty inside child, so the opposite subtree can be attached in one
        # assignment.  SystemRandom makes the choice unpredictable and avoids
        # repeatedly favoring one side during deletion-heavy workloads.
        if left is None:
            return right
        if right is None:
            return left

        if self.random.choice((True, False)):
            # Use the greatest key from the left subtree.
            left = self.Splay(left, self.MaximumKey(left))
            left.right = right
            return left

        # Use the smallest key from the right subtree.
        right = self.Splay(right, self.MinimumKey(right))
        right.left = left
        return right

    def MinimumNode(self, node):
        # Return the first node in a subtree.
        # This is O(height), and returns the actual node rather than its key.
        if node is None:
            return None
        while node.left is not None:
            node = node.left
        return node

    def MaximumNode(self, node):
        # Return the last node in a subtree.
        # This is O(height), and returns the actual node rather than its key.
        if node is None:
            return None
        while node.right is not None:
            node = node.right
        return node

    def MinimumKey(self, node):
        # Return the smallest key in a non-empty subtree in O(height).
        while node.left is not None:
            node = node.left
        return node.key

    def MaximumKey(self, node):
        # Return the largest key in a non-empty subtree in O(height).
        while node.right is not None:
            node = node.right
        return node.key

    def Delete(self, key):
        # The target must first become the root.
        #
        # After a successful splay, the root is detached from both the tree
        # and the sorted list.  The remaining subtrees are joined, while the
        # neighboring list nodes are linked directly around the removed node.
        # The removed value is returned; a missing key returns None and leaves
        # membership unchanged, although the tree may have been splayed.
        if self.root is None:
            return None

        self.root = self.Splay(self.root, key)
        if self.CompareKeys(self.root.key, key) != 0:
            return None

        removed = self.root.value
        left = self.root.left
        right = self.root.right
        previous = self.root.previous
        successor = self.root.next
        if previous is None:
            self.head = successor
        else:
            previous.next = successor
        if successor is None:
            self.tail = previous
        else:
            successor.previous = previous
        self.root.previous = None
        self.root.next = None
        self.root = self.JoinAfterDelete(left, right)
        self.count -= 1
        return removed

    def Update(self, key, value):
        # Update only an existing key and leave it at the root.
        # This changes payload only; list and tree ordering remain untouched.
        self.root = self.Splay(self.root, key)
        if self.root is None or self.CompareKeys(self.root.key, key) != 0:
            return False
        self.root.value = value
        return True

    def RootItem(self):
        # Return the root key and value without changing the tree.
        if self.root is None:
            return None
        return self.root.key, self.root.value

    def Traverse(self):
        # Yield Items sequentially through the linked list.
        # Traversal is O(n) and avoids recursion, so it is safe for a highly
        # skewed tree.  The generator observes live list links while iterating.
        node = self.head
        while node is not None:
            yield node.key, node.value
            node = node.next

    def __iter__(self):
        # Allow sequential traversal with a for loop.
        return self.Traverse()

    def Items(self):
        # Return Items in sorted key order through the linked list.
        # This materializes the complete traversal and therefore uses O(n)
        # additional memory.
        return list(self.Traverse())

    def SavePreOrder(self, path):
        # Save key/value pairs in iterative pre-order as JSONL.
        #
        # The stack pushes right before left so left is processed first.  A
        # value shaped like an ID-keyed database record is emitted unchanged;
        # all other values use the generic ``key``/``value`` envelope expected
        # by LoadJSONL.  The output order reflects tree shape, not sorted order.
        pending = []
        if self.root is not None:
            pending.append(self.root)
        written = 0
        with open(path, "w", encoding="utf-8") as target:
            while pending:
                node = pending.pop()
                if isinstance(node.value, dict) and node.value.get("ID") == node.key:
                    entry = node.value
                else:
                    entry = {"key": node.key, "value": node.value}
                target.write(json.dumps(entry, ensure_ascii=False) + "\n")
                written += 1
                if node.right is not None:
                    pending.append(node.right)
                if node.left is not None:
                    pending.append(node.left)
        return written

    def Validate(self):
        # Verify tree ordering, linked-list links, and node count.
        #
        # The in-order tree walk and forward list walk must contain the exact
        # same node objects in the same order.  Object identity checks catch
        # stale or cross-linked list pointers that value comparisons would
        # miss.  This diagnostic is O(n) time and O(n) temporary memory.
        treeItems = []
        stack = []
        node = self.root
        while stack or node is not None:
            while node is not None:
                stack.append(node)
                node = node.left
            node = stack.pop()
            treeItems.append(node)
            node = node.right

        listItems = []
        previous = None
        node = self.head
        while node is not None:
            if node.previous is not previous:
                return False
            if previous is not None and previous.next is not node:
                return False
            listItems.append(node)
            previous = node
            node = node.next

        if previous is not self.tail:
            return False
        if treeItems != listItems:
            return False
        for index in range(1, len(treeItems)):
            if self.CompareKeys(
                    treeItems[index - 1].key, treeItems[index].key) >= 0:
                return False
        return len(treeItems) == self.count


def TestFile(path):
    # Load any text file, using each non-newline line as a key.
    # Invalid UTF-8 is replaced so one damaged byte cannot abort the test.
    tree = SplayTree()
    with open(path, "r", encoding="utf-8", errors="replace") as source:
        for lineNumber, line in enumerate(source, 1):
            key = line.rstrip("\r\n")
            tree.Insert(key, lineNumber)

    originalItems = tree.Items()

    # Demonstrate replacing the default string comparator before use.  The
    # normal default compares ``str(key)`` values, while this independent tree
    # compares integer keys numerically.  A comparator replacement must happen
    # before loading a tree; changing it does not reorder existing nodes.
    def compareNumbers(left, right):
        return (left > right) - (left < right)

    customTree = SplayTree()
    customTree.CompareKeys = compareNumbers
    for number in (10, 2, 1, 20):
        assert customTree.Insert(number, str(number))
    assert customTree.Items() == [
        (1, "1"), (2, "2"), (10, "10"), (20, "20")]
    assert customTree.Validate()

    # Duplicate Insertion is rejected and cannot replace the original value.
    if originalItems:
        duplicateKey = originalItems[0][0]
        originalValue = tree.Search(duplicateKey)
        assert tree.Insert(duplicateKey, "duplicate") is False
        assert tree.Search(duplicateKey) == originalValue

    # Exercise root lookup, missing lookup, Update, Insert, and Delete.
    if originalItems:
        firstKey = originalItems[0][0]
        lastKey = originalItems[-1][0]
        assert tree.Search(firstKey) is not None
        assert tree.RootItem()[0] == firstKey
        assert tree.Search(lastKey) is not None
        assert tree.RootItem()[0] == lastKey
        assert tree.Update(lastKey, "Updated")
        assert tree.Search(lastKey) == "Updated"

    temporaryKey = "__SPLAY_TEST_INSERT__"
    while tree.Contains(temporaryKey):
        temporaryKey += "x"
    tree.Insert(temporaryKey, "temporary")
    assert tree.Search(temporaryKey) == "temporary"
    assert tree.Delete(temporaryKey) == "temporary"
    assert not tree.Contains(temporaryKey)
    assert tree.Search("__SPLAY_KEY_THAT_DOES_NOT_EXIST__") is None
    assert tree.Validate()

    print("SplayTree test passed")
    print("Loaded lines:", len(originalItems))
    print("Unique keys:", len(tree))
    print("Root:", tree.RootItem())
    return tree



def LoadJSONL(path):
    # Load JSONL records and use each original ID as the tree key.
    #
    # Accepted records are either native ``{"ID": ...}`` records or the
    # generic ``{"key": ..., "value": ...}`` format produced by SavePreOrder.
    # Malformed lines are counted and skipped rather than aborting the load.
    tree = SplayTree()
    validLines = 0
    invalidLines = 0
    duplicateKeys = 0

    with open(path, "r", encoding="utf-8", errors="replace") as source:
        for lineNumber, line in enumerate(source, 1):
            try:
                record = json.loads(line)
                if "ID" in record:
                    key = record["ID"]
                elif "key" in record and "value" in record:
                    key = record["key"]
                    record = record["value"]
                else:
                    raise KeyError("ID")
            except (json.JSONDecodeError, TypeError, KeyError):
                invalidLines += 1
                continue

            if tree.Insert(key, record):
                validLines += 1
            else:
                duplicateKeys += 1

    return tree, validLines, invalidLines, duplicateKeys


def TestJSONL(path):
    # Load the JSONL database and exercise ID-keyed operations.
    # The round-trip check compares serialized values as sets; it verifies
    # payload preservation but deliberately does not require identical tree
    # shape or record order after reconstruction.
    tree, validLines, invalidLines, duplicateKeys = LoadJSONL(path)
    records = tree.Items()

    if records:
        firstKey = records[0][0]
        lastKey = records[-1][0]
        assert tree.Search(firstKey)["ID"] == firstKey
        assert tree.RootItem()[0] == firstKey
        assert tree.Search(lastKey)["ID"] == lastKey
        assert tree.RootItem()[0] == lastKey
        assert tree.Contains(firstKey)

    preorderPath = path + ".preorder.jsonl"
    assert tree.SavePreOrder(preorderPath) == len(tree)
    restoredTree, restoredValid, restoredInvalid, restoredDuplicates = LoadJSONL(
        preorderPath)
    originalData = set()
    for key, value in records:
        originalData.add(json.dumps(value, sort_keys=True, ensure_ascii=False))
    restoredData = set()
    for key, value in restoredTree.Items():
        restoredData.add(json.dumps(value, sort_keys=True, ensure_ascii=False))
    assert restoredValid == validLines
    assert restoredInvalid == 0
    assert restoredDuplicates == 0
    assert originalData == restoredData
    assert restoredTree.Validate()
    assert tree.Validate()
    print("JSONL SplayTree test passed")
    print("Valid records:", validLines)
    print("Unique ID keys:", len(tree))
    print("Invalid lines skipped:", invalidLines)
    print("Duplicate IDs rejected:", duplicateKeys)
    print("First traversed ID:", records[0][0] if records else None)
    print("Last traversed ID:", records[-1][0] if records else None)
    return tree


if __name__ == "__main__":
    # Read Data.JDB by default, or a JSONL path supplied on the command line.
    # This module is intentionally usable as both an importable library and a
    # small command-line validation tool.  More than one argument is rejected
    # with a usage message and exit status 2.
    dataPath = sys.argv[1] if len(sys.argv) == 2 else "/tmp/Work/Data.JDB"
    if len(sys.argv) > 2:
        print("Usage: python st1.py [JSONL_FILE]")
        raise SystemExit(2)
    TestJSONL(dataPath)
