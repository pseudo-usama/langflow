const useDuplicateFlows = (
  selectedFlowsComponentsCards,
  allFlows,
  addFlow,
  resetFilter,
  getFoldersApi,
  getFolderById,
  setSelectedFlowsComponentsCards,
  folderId,
  myCollectionId,
  setSuccessData
) => {
  const handleDuplicate = () => {
    Promise.all(
      selectedFlowsComponentsCards.map((selectedFlow) =>
        addFlow(
          true,
          allFlows.find((flow) => flow.id === selectedFlow)
        )
      )
    ).then(() => {
      resetFilter();
      getFoldersApi(true);
      if (!folderId || folderId === myCollectionId) {
        getFolderById(folderId ? folderId : myCollectionId);
      }
      setSelectedFlowsComponentsCards([]);
      setSuccessData({ title: "Flows duplicated successfully" });
    });
  };

  return { handleDuplicate };
};

export default useDuplicateFlows;
